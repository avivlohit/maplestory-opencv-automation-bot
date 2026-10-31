import cv2
from config.config_loader import config
import logging
import src.utils.logger as logger
from src.utils.common import get_window_handle_and_rect_by,bring_to_front_and_center_origin
import win32gui
from PIL import ImageGrab
import numpy as np
import ctypes
import sys
import os
import time
from src.engine.MinimapDetector import MinimapDetector
import src.action.HotkeyManager as hk
import win32con
from pathlib import Path
import yaml


'''
Operation logger.
Bridges real-time game screen with MinimapDetector.py, recording player coordinates and action logs.

Default modes: walk : walk; rope : rope point; jump_down : jump down directly

[NOTE!] Two consecutive 'walk' actions are treated as a platform; two consecutive 'rope' actions are treated as a vertical channel.
Ensure walk points share approximately the same height (Y), and rope points share the same X coordinate.
 
[Example] ... -> walk -> walk -> rope -> rope:
Two walk points form a platform (combat mode is triggered only on platforms); two rope points form a vertical channel.

Hotkeys:
F1  Save action coordinates under minimap directory
F2  Exit application
F4  Set walk point
F5  Set rope point
F6  Set jump point
F7  Set jump down point
'''



class OperationLogger:
    def __init__(self):

        #--- Window settings
        self.game_title = config.get("game.title")
        self.hwnd = None
        self.frame_size = None
        #--- Path settings
        self.map_name = config.get("quickly_choice_map")
        self.map_url = Path(config.get(f"mini_map.{self.map_name}"))
        self.mini_map = cv2.imread(str(self.map_url))
        #--- Module instances
        self.minimap_detector = None
        self.hk = None

        #--- Data containers
        self.player_loc = None
        self.recored_data = []

    #=================
    # Initialization and Resource Loading
    #=================
    def _connect_window(self):
        '''
        Hook game window
        '''
        self.hwnd,_ =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            logging.info(f"Successfully loaded game title: {self.game_title}, window handle: {self.hwnd}")
        else:
            logging.info(f"Specified window not found: {self.game_title}")

    def _scan_full_screen(self):
        '''
        Read game window via hwnd and capture new game frame
        '''
        try:

            client_rect = win32gui.GetClientRect(self.hwnd)
            client_tl = win32gui.ClientToScreen(self.hwnd, (client_rect[0], client_rect[1]))
            client_br = win32gui.ClientToScreen(self.hwnd, (client_rect[2], client_rect[3]))
            screen_rect  = (client_tl[0], client_tl[1], client_br[0], client_br[1])

        except Exception as e:
            logging.error(f"Screen capture error: {e}")
            return None
        
        # Capture - to array - to BGR

        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) # Image processing defaults to BGR

        if frame_bgr is not None:

            # Record frame dimensions
            if self.frame_size is None:
                y, x = frame_bgr.shape[:2]  # (height, width)
                self.frame_size = (x ,y)

            return frame_bgr

        return frame_bgr

    def _loading_config(self):
        #-- Load modules
        self.minimap_detector = MinimapDetector()
        self.hk = hk.HotkeyManager()
        #-- Load hotkeys
        key_mappings = {
            win32con.VK_F1: self._save_actions_to_yaml,
            win32con.VK_F2: self._exit_app,
            win32con.VK_F4: self._walk_point,
            win32con.VK_F5: self._rope_point,
            win32con.VK_F6: self._jump_point,
            win32con.VK_F7: self._jump_down_point,
            0xBD: self.small_move_to_left,
            0xBB: self.small_move_to_right,
            # win32con.VK_F8: self._jump_down_point,
        }
        
        for vk, func in key_mappings.items():
            self.hk.register(vk, func)
    # === Screen Operations
    def _setting_cv2_map(self):
        '''
        Pre-create empty OpenCV windows with adjustable size and position
        '''
        cv2.namedWindow("Min_iMap", cv2.WINDOW_NORMAL)
        cv2.moveWindow("Min_iMap", 1500, 0)

        cv2.namedWindow("Big_Map", cv2.WINDOW_NORMAL)    
        cv2.moveWindow("Big_Map", 1280, 700)

    def _draw_map(self):
        '''
        Function:
            Display various visualizations
        '''
        cv2.imshow("Min_iMap", self.mini_map)
        self.draw_recorded_points(self.mini_map)
        cv2.imshow("Big_Map", self.frame_bgr)
        self.draw_recorded_points
        cv2.putText(self.frame_bgr, f"Player Pos: {self.player_loc}", org=(10, 275),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=2, color=(0, 0, 255), thickness=2)
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
    
    def run(self):

        #pre_process
        # Force Python process to recognize actual screen DPI pixels to avoid cropped capture bounds
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
        self._setting_cv2_map()
        self._connect_window()
        self._loading_config()
        bring_to_front_and_center_origin(self.hwnd)
        time.sleep(0.5)
        self.print_msg()
        #process
        self.screen_loop()

        print("=" * 45)

    def screen_loop(self):
        '''
        Full screen refresh loop
        '''
        
        try:
            while True:
                #== Guard check ==================
                if not self._is_window_valid():
                    time.sleep(1)
                    continue
                #== Key listener ==================
                self.hk.poll() 
                #== Frame update ==================
                self.frame_bgr = self._scan_full_screen()
                #== Main logic ====================

                player_loc = self.MinimapDetector(self.frame_bgr)
                self.player_loc = player_loc
                self._show_player_loc(self.player_loc)
                
                #===========================
                # Frame display
                self._draw_map()
                cv2.waitKey(1)

        except Exception as e:
            logging.error(f"Exception occurred in screen_loop: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    def MinimapDetector(self,frame)-> tuple[int,int]:
        '''
        Interact with minimap detector: send current BGR frame
        return: player position (x, y)
        '''
        result = self.minimap_detector.run(frame)
        return result
    
    def _show_player_loc(self,player_loc):
        
        cv2.putText(self.frame_bgr, f"Player Pos: {player_loc}", org=(10, 275),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=2, color=(0, 0, 255), thickness=2)
    def draw_recorded_points(self, frame):
        '''
        Function: Draw user-defined recorded coordinates on the frame,
        drawing two consecutive walk points as a platform bounding box,
        and two consecutive rope points as a channel bounding box.
        '''
        if not self.recored_data:
            return frame

        # 1. Draw individual points
        for index, item in enumerate(self.recored_data, start=1):
            loc = item.get('loc')
            action = item.get('action')
            
            if loc is not None:
                x, y = int(loc[0]), int(loc[1])
                # Default colors (prevent crash)

                if action == "walk":
                    color = (128, 128, 128)
                elif action == "rope":
                    color = (51, 0, 25)
                elif action == "JumpRight":
                    color = (204, 204, 0)     
                elif action == "JumpLeft":
                    color = (255, 153, 51)      
                elif action == "JumpDown":
                    color = (255, 51, 153)   
                else:
                    color = (128, 128, 128)  
                cv2.rectangle(frame, (x-3, y-3), (x+3, y+3),  color, 1)



        # 2. Draw consecutive points
        for i in range(len(self.recored_data) - 1):
            current_item = self.recored_data[i]
            next_item = self.recored_data[i + 1]
            
            curr_action = current_item.get('action')
            next_action = next_item.get('action')
            
            curr_loc = current_item.get('loc')
            next_loc = next_item.get('loc')
            
            if curr_loc is None or next_loc is None:
                continue
                
            x1, y1 = int(curr_loc[0]), int(curr_loc[1])
            x2, y2 = int(next_loc[0]), int(next_loc[1])
            
            # Condition A: Two consecutive walks -> Platform
            if curr_action == "walk" and next_action == "walk":
                # Draw rectangle with two points as diagonals
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 1)

            # Condition B: Two consecutive ropes -> Vertical channel
            elif curr_action == "rope" and next_action == "rope":

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 1)


        return frame

                            

    #=================
    # Hotkey Bindings
    #=================
    def _walk_point(self):
        '''
        Platform movement point
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "walk"})
        self._show_last_item()
        self._show_recorded_data()

    def _rope_point(self):
        '''
        Rope climb point
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "rope"})
        self._show_last_item()
        self._show_recorded_data()

    def _jump_point(self):
        '''
        @brief Simple jump
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "Jump"})
        self._show_last_item()
        self._show_recorded_data()


    def _jump_down_point(self):
        '''
        @brief Jump down
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "JumpDown"})
        self._show_last_item()
        self._show_recorded_data()

    def _jump_up_point(self):
        '''
        Jump up
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "JumpUp"})
        self._show_last_item()
        self._show_recorded_data()

    def _jump_to_right_point(self):
        '''
        Jump right
        '''
        self.recored_data.append({"loc": list(self.player_loc), "action": "JumpRight"})
        self._show_last_item()
        self._show_recorded_data()

    def _jump_to_left_point(self):
        '''
        Jump left
        '''
        self.recored_data.append({"loc": list(self.player_loc), "action": "JumpLeft"})
        self._show_last_item()
        self._show_recorded_data()

    def small_move_to_right(self):
        '''
        @brief Small move right
        '''
        self.recored_data.append({"loc": list(self.player_loc), "action": "M_RIGHT"})
        self._show_last_item()
        self._show_recorded_data()

    def small_move_to_left(self):
        '''
        @brief Small move left
        '''
        self.recored_data.append({"loc": list(self.player_loc), "action": "M_LEFT"})
        self._show_last_item()
        self._show_recorded_data()

    #=================
    # Text Output
    #=================
    def print_msg(self):

        print("=" * 45)
        print(" Game Operation & Coordinate Logger - Hotkey Guide:")
        print("=" * 45)
        print(" [F1] Save action coordinates to YAML")
        print(" [F2] Exit application")
        print(" [F4] Action point: Walk (movement point)")
        print(" [F5] Action point: Rope (climb point)")
        print(" [F6] Action point: Jump (simple jump)")

        print("=" * 45)


    def _show_last_item(self):
        if self.recored_data:  # Ensure list is not empty to avoid errors
            self.recored_data_list = self.recored_data[-1]
            print(f"Last recorded -> Action: {self.recored_data_list.get('action')}, Pos: {self.recored_data_list.get('loc')}")

    def _show_recorded_data(self):
        '''
        Function:
            Display recorded data
        '''
        print("=" * 30)
        print(" Currently recorded operation data:")

        for index, item in enumerate(self.recored_data, start=1):
            action = item.get('action', 'Unknown')
            loc = item.get('loc', 'No Pos')
            print(f" [{index:2d}] Action: {action:<15} | Pos: {loc}")

        print("=" * 30)

    def _save_actions_to_yaml(self):
        '''
        Save coordinates and actions to YAML format
        '''
        folder_path = self.map_url.parent
        yaml_path = folder_path / f"{self.map_name}.yaml"
        
        try:
            with open(yaml_path, "w") as f:
                yaml.dump(self.recored_data, f)
            print(f"File saved successfully, path: {yaml_path}")

        except Exception as e:
            logging.error(f"Error saving data: {e}")
        pass

    def _exit_app(self):
        '''
        Function: Exit application
        '''
        logging.info("Closing application...")
        self.bot_enabled = False
        
        # Destroy all OpenCV windows
        cv2.destroyAllWindows()
        import sys
        sys.exit(0)

    #=================
    # OS Administrator Privileges
    #=================
def is_admin():
    """Check if currently running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Rerun current script with administrator privileges."""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

if __name__ == "__main__":
        #--- Administrator privileges
        if not is_admin():
            run_as_admin()
            sys.exit()
        #--- Logger module
        logger.setup_logging()
        #--- run
        run = OperationLogger()
        run.run()
