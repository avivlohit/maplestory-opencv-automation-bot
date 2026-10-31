from config.config_loader import config
import ctypes
# Force Python process to recognize actual screen DPI pixels to avoid cropped capture bounds
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass
from src.engine.GameBot import GameBot
import src.utils.logger as logger
import logging
import cv2
import logging
from pathlib import Path
import src.utils.logger as logger
from src.utils.common import get_window_handle_and_rect_by,bring_to_front_and_center_origin
import win32gui
from PIL import ImageGrab
import numpy as np
from pynput.keyboard import Controller, Key
import time
import win32gui 
'''
WIP
Coconut harvesting script

Start point: 142, 51
First fruit: 142, 51 normal attack
Second fruit: 152, 58 normal attack
Third fruit: 161, 58 normal attack
Fourth fruit: 176, 54 normal attack
'''
class MaibBot:



    def __init__(self):
        # Window info
        self.game_title = config.get("game.title", "MapleStory")
        self.hwnd = None
        self.client_rec = None

        # Map container
        self.minimap = None
        # Frame info
        self.frame_bgr = None
        self.frame_size = None
        self.mini_player_loc = None # <- Player coordinates
        # Module instance container
        self.map_detector = None


    def _instantiation(self):
        '''
        Instantiate modules
        '''
        self.map_detector = MapDectector()
        self.minimap_detector = MinimapDetector()
        self.coco_task_manager = CocoTaskManager()
    def _load_res(self):
        '''
        Load resources
        '''

        self.minimap = self.map_detector.load_map()

    #=================
    # Window Handling
    #=================

    def _setting_windows(self):
        '''
        Function:
            Pre-flight window calibration and preparation
        Returns:
            Game window handle
        '''
        self.hwnd = self.map_detector.connect_window()
        
    def _is_window_valid(self):
        if not win32gui.IsWindow(self.hwnd):
            logging.info("Window not detected")
            return False
        if win32gui.IsIconic(self.hwnd):
            logging.info("Window not detected")
            return False
        rect = win32gui.GetClientRect(self.hwnd)
        if rect[2] < 100 or rect[3] < 100:
            return False
        return True

    def _is_game_window_foreground(self):
        '''
        Check if game window is currently the foreground window
        '''
        return win32gui.GetForegroundWindow() == self.hwnd

    
    def run(self):

        # Preprocessing
        self._instantiation()
        self._load_res()
        self._setting_windows()

        # Main program
        self.loop()

    def loop(self):
        '''Main loop'''
        try:
            while True:

                # Window guard check

                # If window minimized, wait for restore
                if not self._is_window_valid():
                    time.sleep(1)
                    continue

                # is_game_window_foreground = self._is_game_window_foreground() # Check if game window is in foreground this frame
                # if not is_game_window_foreground and self.is_game_window_foreground_last_frame: 
                #     self.keyboard.release_all()
                #     self.keyboard.stop_move()
                # self.is_game_window_foreground_last_frame = is_game_window_foreground  # Update foreground state

                #===================
                # Data collection
                self.frame_bgr = self.map_detector.scan_full_screen()
                self._get_window_rect()
                self.mini_player_loc = self.MinimapDetector() 
                self.coco_task_manager.process(self.mini_player_loc)
                # Image rendering
                # self._render_cv2_view()
                # self._render_minimap_overlay(self.mini_player_loc)
        except Exception as e:
            logging.error(f"Error updating window: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    # Render image

    def _render_cv2_view(self):
        '''
        Function:
            Unified view rendering
        '''
        try:
            if self.mini_player_loc is  None:
                return
            self._show_player_loc(self.mini_player_loc)
            cv2.imshow("CoCoBeater", self.frame_bgr)
            cv2.waitKey(1)
        except Exception as e:
            print(f"Error rendering view: {e}")
            logging.error(f"Error rendering view: {e}", exc_info=True)

    def _render_minimap_overlay(self,mini_player_loc):
        '''
        Minimap rendering
        '''
        # Guard check: intercept missing data to prevent crash
        if self.minimap_detector.crop_frame_bgr is None or mini_player_loc is None:
            return
        overlay = self.minimap_detector.crop_frame_bgr.copy()
        # dx , dy = 8,0

        cv2.circle(overlay, (mini_player_loc[0] , mini_player_loc[1]), 3, [255,255,0], 1)
        cv2.imshow("Minimap Debug", overlay)
    #=================
    # Drawing Functions
    #=================

    def _show_player_loc(self,player_loc):
        
        cv2.putText(self.frame_bgr, f"Player Pos: {player_loc}", org=(10, 300),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 40, 0), thickness=2)
    #========
    # Helper Functions
    #========

    def _get_window_rect(self):
        '''
        Function:
            Detect and record frame size if not already set
        Yields:
            self.frame_size
        '''
        if self.frame_bgr is not None and self.frame_size is None:
            y, x = self.frame_bgr.shape[:2]  # (height, width)
            self.frame_size = (x ,y)

    #=================
    # Detector: Minimap
    #=================
    def MinimapDetector(self)-> tuple[int,int]:
        '''
        WIP
        Interact with minimap detector: send current BGR frame
        return: player position (x, y)
        '''
        mini_player_loc = self.minimap_detector.run(self.frame_bgr)
        return mini_player_loc
    
class MapDectector:
    '''
    Image-related processing
    '''
    def __init__(self):
        # Window info
        self.game_title = config.get("game.title", "MapleStory")
        self.hwnd = None

        self.frame_bgr = None   
        self.client_rect = None 


    def load_map(self):
        '''
        Load map
        '''
        map_name_is = "Florina_Beach_Lorang's_Sandy_Beach"
        minimap_folder = "img/mini_map"
        current_dir = Path.cwd()
        print(current_dir)
        minimap_dir= current_dir / minimap_folder / map_name_is / f"{map_name_is}.png"
        if minimap_dir.exists():
            print("Map loaded successfully")

        else:
            e = f"{minimap_dir} does not exist"
            print(e)
            logging.error(f"{e}")

        minimap = cv2.imread(str(minimap_dir), cv2.IMREAD_COLOR)
        return minimap

    def connect_window(self):
        '''
        Function:
            Hook window and bring to foreground at (0, 0)
        return:
            window handle, window rect

        '''
        self.hwnd, _ =  get_window_handle_and_rect_by(self.game_title)

        if self.hwnd :
            bring_to_front_and_center_origin(self.hwnd)
            print(f"Successfully loaded game title: {self.game_title}, window handle: {self.hwnd}")
            logging.info(f"Successfully loaded game title: {self.game_title}, window handle: {self.hwnd}")

        else:
            print(f"Specified window not found: {self.game_title}")
            logging.info(f"Specified window not found: {self.game_title}")

        return self.hwnd
    
    def scan_full_screen(self):
        '''
        Function:
            Scan game screen and update
        Requirements:
            Window and handle
        '''
        try:

            client_rect = win32gui.GetClientRect(self.hwnd)
            client_tl = win32gui.ClientToScreen(self.hwnd, (client_rect[0], client_rect[1]))
            client_br = win32gui.ClientToScreen(self.hwnd, (client_rect[2], client_rect[3]))
            screen_rect  = (client_tl[0], client_tl[1], client_br[0], client_br[1])
            self.client_window_tl = client_tl
        except Exception as e:
            logging.error(f"Exception occurred in screen_loop: {e}", exc_info=True)
            return None

        # Capture - to array - to BGR
        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) # Image processing defaults to BGR

        return frame_bgr

class MinimapDetector:
    def __init__(self):

        self.current_frame_bgr =None
        self.crop_frame_bgr = None

        #load config
        self._load_minimap_config()

    def _load_minimap_config(self):
        '''
        Load minimap
        '''
        try:
            #load map img

            map_name_is = "Florina_Beach_Lorang's_Sandy_Beach"
            minimap_folder = "img/mini_map"
            current_dir = Path.cwd()

            map= current_dir / minimap_folder / map_name_is / f"{map_name_is}.png"

            self.minimap_template = cv2.imread(map,cv2.IMREAD_COLOR)
        except Exception as e:
            logging.error(f"Failed to load map: {e}")


    def _crop_minimap(self,frame_bgr):
        '''
        Input: Full color image
        Action: Crop minimap region and store in self.crop_frame_bgr
        '''
        h,w = self.minimap_template.shape[:2]
        crop_offset = config.get("minimap.crop_offset", [6, 72]); x1, y1 = crop_offset[0], crop_offset[1] #<-- Hardcoded here
        return frame_bgr[y1 : y1 + h, x1 : x1 + w]

    def run(self,frame_bgr):

        self.crop_frame_bgr = self._crop_minimap(frame_bgr)

        # Guard check: skip detection if no frame
        if self.crop_frame_bgr is None:
            return
        
        # Get player coordinates
        player_loc = self._detect_player_loc(self.crop_frame_bgr)

        return player_loc

    # 
    def _detect_player_loc(self, frame):
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_player_color = np.array([25, 100, 180])
        upper_player_color = np.array([35, 255, 255])
        mask = cv2.inRange(frame_hsv, lower_player_color, upper_player_color)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Filter player color block range
        MIN_AREA, MAX_AREA = 2, 15

        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if not (MIN_AREA <= area <= MAX_AREA):
                continue


            perimeter = cv2.arcLength(c, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * area / (perimeter ** 2)  # 1.0 = perfect circle
            if circularity < 0.5: 
                continue

            M = cv2.moments(c)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            candidates.append((cx, cy, area))

        if not candidates:
            return None

        # If multiple color blocks found, select the one closest to player profile
        EXPECTED_AREA = 8
        best = min(candidates, key=lambda p: abs(p[2] - EXPECTED_AREA))
        return (best[0], best[1])
    




class ActionController:
    def __init__(self):
        self.keyboard = Controller()
        self.game_title = config.get("game.title", "MapleStory")  # Game title
        self.is_holding_z = False

    def _is_game_active(self):
        """Guard check: check if current foreground window title matches game"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            # Only allow actions if current foreground window title contains game title
            return self.game_title in title
        except Exception:
            return False

    def press_key(self, key, duration=0.1):
        """Press and release key (with guard check)"""
        if not self._is_game_active():
            print("Guard intercept: Current window is not game, keypress skipped")
            return
            
        self.keyboard.press(key)
        time.sleep(duration)
        self.keyboard.release(key)

    def jump_attack(self):
        """Jump attack"""
        if not self._is_game_active():
            return
            
        self.keyboard.press(Key.alt)
        time.sleep(0.2)
        self.keyboard.press(Key.ctrl) 
        time.sleep(0.05)
        self.keyboard.release(Key.alt)
        self.keyboard.release(Key.ctrl)

    def normal_attack(self):
        """Normal attack"""
        self.press_key(Key.ctrl, 0.05)  

    def start_hold_z(self):
        """Start background thread to hold Z key continuously"""
        if self.is_holding_z:
            return
        
        self.is_holding_z = True
        
        def _hold():
            while self.is_holding_z:
                if self._is_game_active():
                    self.keyboard.press('z')
                    time.sleep(0.1)
                else:
                    # Release Z key automatically if switched away to avoid stuck keys
                    self.keyboard.release('z')
                    time.sleep(0.5)
            self.keyboard.release('z')

        import threading
        self.z_thread = threading.Thread(target=_hold, daemon=True)
        self.z_thread.start()
    def stop_hold_z(self):
        """Stop holding Z key in background"""
        self.is_holding_z = False


class CocoTaskManager:
    '''
    Responsible for calculating distance to fruit and triggering actions
    '''
    def __init__(self):
        self.action = ActionController()
        self.channel_count = 0
        #flat 
        self.coco_beater_flag = False  # <- Start hitting fruit
        self.change_flag = False # <- Change channel
    def process(self, player_loc):
        '''
        Control center
        '''
        if not player_loc:
            return


        # Player at origin -> Start script actions
        if self._start_position(player_loc) and not self.coco_beater_flag:
            self.coco_beater_flag = True
            self._auto_action(player_loc)

        time.sleep(3)
        # Player at destination -> Prepare to change channel

        if self._end_position(player_loc) and not self.change_flag:
            self.change_flag = True
            self._change_channel()

    def _start_position(self, player_loc, tolerance=2):
        """
        Check if player is near initial origin
        tolerance: Allowed error in pixels (default: 2)
        """
        if not player_loc:
            return False
            
        target_x, target_y = 142, 51
        player_x, player_y = player_loc

        # Check if X and Y distance are both within tolerance
        if abs(player_x - target_x) <= tolerance and abs(player_y - target_y) <= tolerance:
            print(f"Origin reached (current pos: {player_loc})")
            return True
        else:
            return False

    def _auto_action(self,player_loc):
        '''
        Scripted coconut harvesting actions
        '''

        count = 7  # Attack count
        self.action.start_hold_z()
        # First fruit: 146, 51
        for i in range(count):
            time.sleep(0.5)
            self.action.normal_attack()
            time.sleep(0.5)

        time.sleep(1) # Wait for fruit to drop

        # Second fruit: 152, 58
        self.action.press_key(Key.right,1.7)
        self.action.press_key(Key.left,0.1)
        for i in range(count):
            time.sleep(0.5)
            self.action.normal_attack()
            time.sleep(0.5)

        # Third fruit: 176, 54
        self.action.press_key(Key.right,0.7)
        for i in range(count):
            time.sleep(0.5)
            self.action.normal_attack()
            time.sleep(0.5)

        # Fourth fruit: 178, 54
        self.action.press_key(Key.right,0.3)
        for i in range(5):
            time.sleep(0.5)
            self.action.normal_attack()
            time.sleep(0.5)

        self.action.stop_hold_z()

        self.coco_beater_flag = False

    def _end_position(self, player_loc, tolerance=2):
        """
        Check if player is near end point
        tolerance: Allowed error in pixels (default: 2)
        """
        if not player_loc:
            return False
            
        target_x, target_y = 160, 58
        player_x, player_y = player_loc

        # Check if X and Y distance are both within tolerance
        if abs(player_x - target_x) <= tolerance and abs(player_y - target_y) <= tolerance:
            print(f"Origin reached (current pos: {player_loc})")
            return True
        else:
            return False

    def _change_channel(self):
        '''
        Channels 1-60 can be switched using right arrow, but stops at end.
        Default begins at channel 1, counts up to 60 then resets.
        '''
        self.channel_count += 1
        print(f"Channel change count: {self.channel_count}")

        # Open channel menu
        self.action.press_key(Key.esc,0.03)
        time.sleep(0.2)
        self.action.press_key(Key.enter,0.03)
        # Select channel

        self.action.press_key(Key.right,0.03)

        # Switch
        self.action.press_key(Key.enter,0.03)

        time.sleep(2) # Wait for channel change
        # Toggle FLAG
        self.change_flag = False

if __name__ == "__main__":

    # I. Initialize logging
    logger.setup_logging()
    try:
        run = MaibBot()
        run.run()
    except Exception as e:
        logging.exception(f"Script launch failed: {e}")
