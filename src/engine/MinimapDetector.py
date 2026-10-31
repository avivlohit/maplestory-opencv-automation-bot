from config.config_loader import config
import cv2
import logging
import numpy as np
from src.utils.shared_info import shared_info

class MinimapDetector:
    def __init__(self):
        self.current_frame_bgr = None
        self.crop_frame_bgr = None
        self.crop_offset = [6, 72]

        # load config
        self._load_minimap_config()

    def _load_minimap_config(self):
        '''
        Load minimap template and crop offset from config
        '''
        try:
            map_name = config.get("quickly_choice_map")
            map_path = config.get(f"mini_map.{map_name}")

            self.minimap_template = cv2.imread(map_path, cv2.IMREAD_COLOR)
            self.crop_offset = config.get("minimap.crop_offset", [6, 72])
        except Exception as e:
            logging.error(f"Failed to load minimap config: {e}")

    def _crop_minimap(self, frame_bgr):
        '''
        Crop minimap using configured top-left coordinates
        '''
        if self.minimap_template is None:
            return None
        h, w = self.minimap_template.shape[:2]
        x1, y1 = self.crop_offset[0], self.crop_offset[1]
        return frame_bgr[y1 : y1 + h, x1 : x1 + w]

    def run(self, frame_bgr):
        self.crop_frame_bgr = self._crop_minimap(frame_bgr)

        # Return None if frame is missing or empty
        if self.crop_frame_bgr is None:
            return None
        
        # Detect player coordinates on minimap
        player_loc = self._detect_player_loc(self.crop_frame_bgr)
        return player_loc

    def _detect_player_loc(self, frame):
        '''
        Locate player coordinates via HSV yellow dot detection
        '''
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_player_color = np.array([25, 100, 180])
        upper_player_color = np.array([35, 255, 255])

        mask = cv2.inRange(frame_hsv, lower_player_color, upper_player_color)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Pick the largest yellow contour as the player dot
        largest = max(contours, key=cv2.contourArea)

        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        player_x = int(M["m10"] / M["m00"])
        player_y = int(M["m01"] / M["m00"])

        return (player_x, player_y)
