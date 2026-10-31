import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import time
import yaml
import cv2
import numpy as np
import win32gui
import win32con
from PIL import ImageGrab
from src.utils.common import get_mask, get_window_handle_and_rect_by, bring_to_front_and_center_origin
from config.config_loader import config
import logging

'''
Character Nametag Capture Tool:
Captures game screen. Navigate to an area where your nameplate is clearly visible,
then press 'Z' to capture and process your character nametag.
'''



class GetRoleImg():
    def __init__(self):
        #config
        self.game_title = config.get("game.title")  # Game window title
        self.template_nametag_path = config.get("folder_path.template_nametag_path") # Nametag template
        self.hwnd,self.client_rect =None, None
        self.MyRole_img_path = config.get("folder_path.my_character_template_path") # Save path
        
        #img
        self.role_template = None
        self.role_template_hsv = None
        self.mask = None
        self.img_char_template_mask = None


        #char location 
        self.role_top_left = None
        self.role_bottom_right =None

        #paramter
        self.max_threshold = config.get("image_processing.max_threshold")


    def run(self):
        # pre_load
        self.connect_window()
        bring_to_front_and_center_origin(self.hwnd)
        self.preload_img()

        #main run
        self.get_new_char_img()

    def connect_window(self):
        self.hwnd, self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"Successfully loaded game title: {self.game_title}, window handle: {self.hwnd}")
        else:
            print(f"Specified window not found: {self.game_title}")

    def preload_img(self):
        # Read template
        self.role_template_bgr = cv2.imread(self.template_nametag_path)

        # Convert to grayscale for mask generation
        self.role_template = cv2.cvtColor(self.role_template_bgr, cv2.COLOR_BGR2GRAY)
        
        # Use a grayscale threshold to create the mask (works great for white text on dark backgrounds)
        # Any pixel brighter than 100 becomes part of the "keep" area (white/255)
        _, self.mask = cv2.threshold(self.role_template, 100, 255, cv2.THRESH_BINARY)


    def _save_role_NameTag(self,frame_bgr):
        '''Capture character nametag'''

        x1,y1 = self.role_top_left
        x2,y2 = self.role_bottom_right
        crop_img = frame_bgr[y1:y2,x1:x2]

        result =cv2.imwrite(self.MyRole_img_path,crop_img)
        if result:
            print(f"\nCharacter nametag saved to: {self.MyRole_img_path}")
        else:
            print("Failed to save character nametag")



    def _process_nametag(self):
        '''Post-process image'''
        img = cv2.imread(self.MyRole_img_path)
        if img is None:
            print("Failed to load image")
            return

        # 1. Create a pure green canvas (BGR: 0, 255, 0)
        # Dimensions match original image
        processed_img = np.full(img.shape, (0, 255, 0), dtype=np.uint8)

        h, w, _ = img.shape
        

        # 2. Overlay target regions of original image onto green canvas
        y_name_start, y_name_end = int(h * 0.1), int(h * 0.45) # Character name Y start/end
        x_name_start, x_name_end = int(w * 0.2), int(w * 0.8) # Character name X start/end
        x_badge_start, x_badge_end = int(w * 0.05), int(w * 0.95)  # Medal X start/end
        y_badge_start, y_badge_end = int(h * 0.55), int(h * 0.88)    # Medal Y start/end

        # 3. Overlay selected regions onto green canvas, keeping remainder pure green background
        processed_img[y_name_start:y_name_end, x_name_start:x_name_end] = img[y_name_start:y_name_end, x_name_start:x_name_end]
        processed_img[y_badge_start:y_badge_end, x_badge_start:x_badge_end] = img[y_badge_start:y_badge_end, x_badge_start:x_badge_end]
        # Save processed image
        cv2.imwrite(self.MyRole_img_path, processed_img)
        print(f"\nCharacter nametag saved to: {self.MyRole_img_path}")


    def _capture_screen(self) -> cv2.Mat:
        '''Capture game client window, convert color format, and return processed frame'''

        try:
            camera_rect = win32gui.GetClientRect(self.hwnd)
            camera_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (camera_rect[0], camera_rect[1]))
            camera_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (camera_rect[2], camera_rect[3]))
            camera_rect = (camera_rect_point_top_left[0], camera_rect_point_top_left[1], camera_rect_point_bottom_right[0], camera_rect_point_bottom_right[1])  

        except Exception:
            raise RuntimeError("Window closed or lost.")

        # Capture - to array - to BGR
        current_frame = ImageGrab.grab(bbox=camera_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) # Image processing defaults to BGR

        # Crop screen [y, x]
        # Dynamically crop around center region or keep full frame
        fh, fw = frame_bgr.shape[:2]
        if fh >= 600 and fw >= 900:
            cy, cx = fh // 2, fw // 2
            # Expanded the search area slightly to ensure nametags aren't cut off
            crop_frame = frame_bgr[max(0, cy - 150):min(fh, cy + 150), max(0, cx - 250):min(fw, cx + 250)]
        else:
            crop_frame = frame_bgr
        return crop_frame 

    def _get_role_NameTag(self,frame_bgr):
        '''Detect character position'''
        crop_frame = cv2.cvtColor(frame_bgr,cv2.COLOR_BGR2GRAY)
        method = cv2.TM_CCOEFF_NORMED
        result = cv2.matchTemplate(crop_frame, self.role_template, method, mask=self.mask)

        # Handle infinite values using boolean indexing
        result[result > 1] = 0
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        # Process position coordinates
        self.role_top_left = max_loc
        h, w = self.role_template.shape[:2]
        self.role_bottom_right = (self.role_top_left[0] + w, self.role_top_left[1] + h)

        # Draw bounding box
        cv2.rectangle(frame_bgr, (self.role_top_left[0]-1, self.role_top_left[1]-1),
                    (self.role_bottom_right[0]+1, self.role_bottom_right[1]+1), (100, 0, 255), 2)
        cv2.putText(frame_bgr,f"Match:{max_val:.2f}",(self.role_top_left[0]-10, self.role_top_left[1]-10),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(0, 0, 225), thickness=1)
        # cv2.imshow("Mask (White = Keep, Black = Ignore)", self.mask)
        # cv2.imshow("roler", self.role_template)
    def get_new_char_img(self):
        '''Display view, manual capture'''
        while True:
            try:
                crop_frame  = self._capture_screen()
                self._get_role_NameTag(crop_frame )
                cv2.imshow("Game Debug View", crop_frame )

                # Capture key 'Z'
                key = cv2.waitKey(1) & 0xFF
                if key == ord('z'):
                    self._save_role_NameTag(crop_frame )
                    self._process_nametag()
                    break

                # Exit key 'Q'
                elif key == ord('q'):
                    break
            except RuntimeError as e:
                print(e)
                break

        cv2.destroyAllWindows()



if __name__ == "__main__":
    run =GetRoleImg()
    time.sleep(2)
    run.run()
