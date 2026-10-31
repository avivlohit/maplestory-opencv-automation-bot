import yaml
import os
import cv2
import numpy as np
from config.config_loader import config
import logging
from src.utils.common import cent_coord
import time
from concurrent.futures import ThreadPoolExecutor

'''
mob template resource :https://maplestory.wiki/GMS/65/mob/100101

'''


class MobDetector:
    def __init__(self):
        # Config
        Map_Name = config.get("quickly_choice_map")
        self.min_threshold = config.get("image_processing.mob_min_threshold", "pixel_distance_filter")
        self.mobs_in_map = config.get(f"map.{Map_Name}")

        # filter config
        self.filter_method = config.get("mob_filter_method.method")

        # Guard check
        valid_methods = ["nms", "pixel_distance_filter"]
        if self.filter_method not in valid_methods:
            logging.warning(f"Unsupported filter method '{self.filter_method}', defaulting to 'pixel_distance_filter'")
            self.filter_method = "pixel_distance_filter"

        self.nms_threshold = config.get("nms_threshold")  # <- NMS threshold
        self.pix_filter_threshold = config.get("pix_filter_threshold", 25)  # <- Center distance threshold
        # Template dictionary key: mob_name; value: (grayscale_img, mask or None)
        self.mobs_templates: dict[str, tuple[np.ndarray, np.ndarray | None]] = {}
        self._load_mob_templates()

        cv2.setNumThreads(1)

    def _load_mob_templates(self):
        '''
        Read mob templates from directory into dictionary
        key: mob ID; value: img
        '''
        if not os.path.exists(self.mobs_in_map):
            logging.info(f"{self.mobs_in_map} map folder does not exist")
            return

        for mobs in os.listdir(self.mobs_in_map):
            if mobs.lower().endswith("png"):
                img_path = os.path.join(self.mobs_in_map, mobs)
                mob_name = os.path.splitext(mobs)[0]

                # Load with UNCHANGED to preserve alpha channel if transparent background exists
                raw_img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
                if raw_img is None:
                    continue

                if raw_img.ndim == 3 and raw_img.shape[2] == 4:
                    # Has alpha channel: extract mask, convert BGR to grayscale
                    b, g, r, a = cv2.split(raw_img)
                    mob_img = cv2.cvtColor(cv2.merge([b, g, r]), cv2.COLOR_BGR2GRAY)
                    mask = a
                else:
                    # No alpha channel: fallback to standard grayscale, mask is None
                    mob_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    mask = None

                if mob_img is not None:
                    self.mobs_templates[mob_name] = (mob_img, mask)

    def run(self):
        self._load_mob_templates()

    def searching_mob(self, crop_frame_gray):
        '''
        Accept ROI crop frame and coordinates
        Return detected mob coordinates
        '''
        all_detected_boxes = []

        # Define processing function for a single template (both original and flipped)
        def process_template(item):
            mob_name, (img, mask) = item
            h, w = img.shape[:2]
            flipped_img = cv2.flip(img, 1)
            flipped_mask = cv2.flip(mask, 1) if mask is not None else None
            boxes = []

            method = cv2.TM_CCORR_NORMED if mask is not None else cv2.TM_CCOEFF_NORMED

            # start = time.time()
            # [Original template matching]
            if mask is not None:
                matches_normal = cv2.matchTemplate(crop_frame_gray, img, method, mask=mask)
                # Mask matching can produce anomalies like infinity due to mathematical formulas; clean up anomalies
                matches_normal[matches_normal > 1] = 0  # Handle infinite values
            else:
                matches_normal = cv2.matchTemplate(crop_frame_gray, img, method)
            loc_n = np.where(matches_normal >= self.min_threshold)
            for y, x in zip(loc_n[0], loc_n[1]):
                boxes.append({
                    "mob_name": mob_name,
                    "top_left": (int(x), int(y)),
                    "center": cent_coord((int(x), int(y)), (w, h)),
                    "size": (w, h),
                    "score": float(matches_normal[y, x])
                })

            # print(f"{mob_name} elapsed: {time.time() - start:.3f}")
            # [Flipped matching] Two modes: with mask or without mask
            if flipped_mask is not None:
                matches_flipped = cv2.matchTemplate(crop_frame_gray, flipped_img, method, mask=flipped_mask)
                matches_flipped[matches_flipped > 1] = 0  # Handle infinite values
            else:
                matches_flipped = cv2.matchTemplate(crop_frame_gray, flipped_img, method)
            loc_f = np.where(matches_flipped >= self.min_threshold)
            for y, x in zip(loc_f[0], loc_f[1]):
                boxes.append({
                    "mob_name": mob_name,
                    "top_left": (int(x), int(y)),
                    "center": cent_coord((int(x), int(y)), (w, h)),
                    "size": (w, h),
                    "score": float(matches_flipped[y, x])
                })
            return boxes

        # Use thread pool to process all templates in parallel
        with ThreadPoolExecutor() as executor:

            results = executor.map(process_template, self.mobs_templates.items())
            for res in results:
                all_detected_boxes.extend(res)

        if self.filter_method == "nms":
            result = self._nms_filter(all_detected_boxes)
        elif self.filter_method == "pixel_distance_filter":
            result = self._pix_filter_method(all_detected_boxes)

        return result

    def _pix_filter_method(self, all_detected_boxes: list):
        '''
        Filter method: Center distance threshold (global cross-template filter, maintains output structure)
        '''
        # Packaging container 
        all_mobs_locs = []

        # Holds all filtered boxes
        accepted_boxes = []

        for box in all_detected_boxes:
            cx, cy = box["center"]

            is_dup = False

            # Compare with accepted boxes to filter overlapping boxes
            for existing in accepted_boxes:
                ex_cx, ex_cy = existing["center"]

                # If center distance is below threshold, treat as duplicate afterimage and discard
                if abs(cx - ex_cx) < self.pix_filter_threshold and abs(cy - ex_cy) < self.pix_filter_threshold:
                    is_dup = True
                    break

            if not is_dup:
                accepted_boxes.append(box)

            # Re-group by mob_name
        final_mobs_dict = {}
        for box in accepted_boxes:
            mob_name = box["mob_name"]
            if mob_name not in final_mobs_dict:
                final_mobs_dict[mob_name] = []
            final_mobs_dict[mob_name].append(box)

        # Package results
        all_mobs_locs = [(mob_name, boxes) for mob_name, boxes in final_mobs_dict.items() if boxes]
        return all_mobs_locs

    def _nms_filter(self, all_detected_boxes: list):
        '''
        Filter method: NMS (Non-Maximum Suppression)
        '''
        if not all_detected_boxes:
            return []
        # Sort descending by confidence score
        sorted_boxes = sorted(all_detected_boxes, key=lambda x: x["score"], reverse=True)

        final_filtered_boxes = []
        mobs_by_name = {}

        for box in sorted_boxes:
            name = box["mob_name"]
            if name not in mobs_by_name:
                mobs_by_name[name] = []
            mobs_by_name[name].append(box)

            # Unpack mob and target info
        for mob_name, boxes in mobs_by_name.items():
            mob_sorted_boxes = sorted(boxes, key=lambda x: x["score"], reverse=True)
            matching_boxes = []

            for i in mob_sorted_boxes:
                keep = True

                i_x1, i_y1 = i["top_left"]
                i_x2, i_y2 = i_x1 + i["size"][0], i_y1 + i["size"][1]
                area_i = (i_x2 - i_x1) * (i_y2 - i_y1)

                for target in matching_boxes:

                    t_x1, t_y1 = target["top_left"]
                    t_x2, t_y2 = t_x1 + target["size"][0], t_y1 + target["size"][1]
                    area_target = (t_x2 - t_x1) * (t_y2 - t_y1)

                    # Intersection calculation
                    inter_x1 = max(t_x1, i_x1)
                    inter_y1 = max(t_y1, i_x1)
                    inter_x2 = min(t_x2, i_x2)
                    inter_y2 = min(t_y2, i_y2)

                    inter_w = max(0, inter_x2 - inter_x1)
                    inter_h = max(0, inter_y2 - inter_y1)
                    inter_area = inter_w * inter_h

                    # Union calculation
                    union_are = area_target + area_i - inter_area

                    if union_are > 0:
                        iou = inter_area / union_are
                    else:
                        iou = 0

                    # If overlap exceeds threshold, filter out
                    if iou >= self.nms_threshold:
                        keep = False

                        break
                if keep:
                    matching_boxes.append(i)
            final_filtered_boxes.extend(matching_boxes)
        final_mobs_dict = {}
        for box in final_filtered_boxes:
            mob_name = box["mob_name"]
            if mob_name not in final_mobs_dict:
                final_mobs_dict[mob_name] = []
            final_mobs_dict[mob_name].append(box)

        all_mobs_locs = [(mob_name, boxes) for mob_name, boxes in final_mobs_dict.items() if boxes]
        return all_mobs_locs
