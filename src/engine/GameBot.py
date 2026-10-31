import ctypes

import cv2
import numpy as np
import win32gui
from PIL import ImageGrab
from src.utils.common import (get_window_handle_and_rect_by,
                              bring_to_front_and_center_origin, cent_coord, get_bbox_from_center, draw_dectection_box,
                              BGR2Binary, convert_img2xy
                              )
from src.engine.MobHunting import MobDetector
from src.utils.boxes import BBox
from config.config_loader import config
import logging
from src.action.ActionHandler import ActionHandler
from src.engine.AutoControl import AutoControl
from src.engine.HealthDetector import HealthDetector
from src.engine.game_state import GameState
from src.engine.MinimapDetector import MinimapDetector
import src.action.KeyBoardController as kb
import time
import re
import src.action.HotkeyManager as hk
import win32con, win32gui

'''
Hotkeys:
F9:  Pause / Resume
F12: Exit
'''

'''Mask threshold values'''
LOWER_GREEN = np.array([35, 100, 100], dtype=np.uint8)
UPPER_GREEN = np.array([85, 255, 255], dtype=np.uint8)


class GameBot:

    def __init__(self):
        # ---config setting

        # -- Window settings
        self.game_title = config.get("game.title")
        self.hwnd = None  # <- Game window handle container
        self.client_window_tl = None  # <- Client top-left origin (offset)
        # -- ROI parameters

        self.roi_left_offset = config.get("game_bot.roi_x_offset_l_width")
        self.roi_right_offset = config.get("game_bot.roi_x_offset_r_width")
        self.roi_top_offset = config.get("game_bot.roi_y_offset_t_high")
        self.roi_bottom_offset = config.get("game_bot.roi_y_offset_b_high")
        # -- Rendering parameters
        self.ACTION_POINT_RANGE = config.get("auto_control_config.ACTION_POINT_RANGE", 1)

        # --- Character attributes
        self.my_character_template_path = 'img/nametag/MyRoleNameTag.png'
        self.my_character_template = None
        self.my_character_template_size = None
        self.my_character_template_gray = None
        self.mask = None

        # --- Frame data
        self.frame_bgr = None
        self.roi_crop_frame_gray = None
        self.frame_size: tuple[int, int] = None  # (x,y)typle

        # --- Scan settings
        self.method = cv2.TM_CCOEFF_NORMED
        self.min_threshold = config.get("image_processing.role_min_threshold")

        # --- Computed data
        self.role_BBOX: BBox = None
        self.roi_BBOX: BBox = None
        self.role_score = 0  # Character confidence score
        self.player_center_loc = None
        self.current_mobs_result = None

        self.prev_pcl = None  # Player position from previous frame
        self.prev_roi_BBOX = None  # ROI BBox from previous frame
        self.loss_tracking_count = 0  # Lost tracking frame count
        # --- Health parameters
        self.player_hp = None
        self.player_mp = None

        # -- Module instances
        self.mob_detector = None
        self.player_states = None
        self.health_dectector = None
        self.minimap_detector = None

        # --- Window state
        self.bot_enabled = True  # <- Bot state: True normal operation; False loop paused
        self.is_game_window_foreground_last_frame = True  # <- Record if game window was foreground in previous frame

        # --- Hotkey settings
        self.hotkey_manager = hk.HotkeyManager()
        self.hotkey_manager.register(win32con.VK_F9, self._toggle_bot)
        self.hotkey_manager.register(win32con.VK_F12, self._exit_app)

    # =================
    # Initialization & Loading
    # =================

    def _connect_window(self):
        '''
        hook the game window
        '''
        self.hwnd, self.client_rect = get_window_handle_and_rect_by(self.game_title)
        if self.hwnd:
            logging.info(f"Successfully loaded game title: {self.game_title}, window handle: {self.hwnd}")
        else:
            logging.info(f"Specified window not found: {self.game_title}")

    def _load_game_resources(self):
        """Preload resources"""

        # Load character nametag template (fallback to example template if not yet captured)
        import os
        template_to_load = self.my_character_template_path
        if not os.path.exists(template_to_load):
            example_path = config.get('folder_path.template_nametag_path', 'img/nametag/example.png')
            if os.path.exists(example_path):
                logging.warning(
                    f'Template {template_to_load} not found! Falling back to {example_path}. Please run GetNameTag.py '
                    f'to capture your character nameplate.')
                template_to_load = example_path
            else:
                logging.error(f'Character template not found at {template_to_load} or {example_path}')

        self.my_character_template = cv2.imread(template_to_load)
        if self.my_character_template is None:
            raise FileNotFoundError(f'Failed to read template image from: {template_to_load}')
        self.my_character_template_size = convert_img2xy(self.my_character_template)
        self.my_character_template_gray = cv2.cvtColor(self.my_character_template, cv2.COLOR_BGR2GRAY)

        # Create mask
        my_character_template_hsv = cv2.cvtColor(self.my_character_template, cv2.COLOR_BGR2HSV)
        role_green_mask = cv2.inRange(my_character_template_hsv, LOWER_GREEN, UPPER_GREEN)
        self.mask = cv2.bitwise_not(role_green_mask)

        # Instantiate modules
        self.mob_detector = MobDetector()
        self.action_handler = ActionHandler()
        self.health_dectector = HealthDetector()
        self.auto_control = AutoControl()
        self.minimap_detector = MinimapDetector()
        self.keyboard = kb.KeyBoard()
        logging.info("Attributes and instances loaded")

    # =================
    # Hotkey Control
    # =================

    def _toggle_bot(self):
        '''
        Function: Toggle bot state, default F9
        '''
        try:
            self.bot_enabled = not self.bot_enabled

            # Release all pressed keys
            self.keyboard.release_all()
            self.keyboard.stop_move()

            # Info-level message placed in warning to avoid filter suppression
            logging.warning(f"[Bot State]: {'Started' if self.bot_enabled else 'Paused'}")
        except Exception as e:
            logging.error(e)

    def _exit_app(self):
        '''
        Function: Exit application
        '''
        logging.info("Closing application...")
        self.bot_enabled = False
        time.sleep(0.05)
        # Release all pressed keys
        self.keyboard.release_all()
        time.sleep(0.05)
        # Destroy all OpenCV windows
        cv2.destroyAllWindows()

        # Terminate process
        import sys
        sys.exit(0)

    # =================
    # Window Handling
    # =================
    def _scan_full_screen(self):
        '''Scan game window screen using window handle'''
        try:
            # TODO: Optimize screen capture rect calculation
            client_rect = win32gui.GetClientRect(self.hwnd)
            client_tl = win32gui.ClientToScreen(self.hwnd, (client_rect[0], client_rect[1]))
            client_br = win32gui.ClientToScreen(self.hwnd, (client_rect[2], client_rect[3]))
            screen_rect = (client_tl[0], client_tl[1], client_br[0], client_br[1])
            self.client_window_tl = client_tl
        except Exception as e:
            logging.error(f"Exception occurred in screen_loop: {e}", exc_info=True)
            return None

        # Capture - to array - to BGR
        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR)  # Image processing defaults to BGR

        if frame_bgr is not None:
            self.frame_bgr = frame_bgr

            # Record frame dimensions
            if self.frame_size is None:
                y, x = frame_bgr.shape[:2]  # (height, width)
                self.frame_size = (x, y)
        return frame_bgr

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
        Function: Check if game window is currently the foreground window
        return: bool
        '''
        return win32gui.GetForegroundWindow() == self.hwnd

    def _render_cv2_view(self, mini_player_loc, action_states):
        '''
        Function: Unified rendering
        '''
        # Guard check: discard if missing required data

        self._draw_mob(self.current_mobs_result)
        self._show_player_loc(mini_player_loc)
        self._show_player_action_states(action_states)
        self._show_player_HP(self.player_hp)
        self._show_player_MP(self.player_mp)
        if self.role_BBOX:
            self._draw_player()
        if self.roi_BBOX:
            self._draw_player_roi_bbox()
        if self.player_center_loc:
            # Player center point
            cv2.circle(self.frame_bgr, self.player_center_loc, 5, [42, 42, 165], 3)
        cv2.imshow("Game Debug View", self.frame_bgr)

        cv2.waitKey(1)

    def _render_minimap_overlay(self, mini_player_loc):
        '''
        Minimap rendering
        '''
        # Guard check: intercept missing data to prevent crash
        if self.minimap_detector.crop_frame_bgr is None or mini_player_loc is None:
            return
        overlay = self.minimap_detector.crop_frame_bgr.copy()
        # dx , dy = 8,0
        for layer in self.auto_control.get_debug_geometry():  # <- Unpack nested geometry data returned by function
            if "boxes" in layer:
                for top_left, bottom_right in layer["boxes"]:
                    cv2.rectangle(overlay, top_left, bottom_right, layer["color"], 1)  # <- Draw directly
            if "circle" in layer:
                for center in layer["circle"]:
                    cv2.circle(overlay, center, self.ACTION_POINT_RANGE, layer["color"], 1)

        cv2.circle(overlay, (mini_player_loc[0], mini_player_loc[1]), 3, [255, 255, 0], 1)
        cv2.imshow("Minimap Debug", overlay)

    def _setting_cv2_map(self):
        '''
        Pre-create empty OpenCV windows with adjustable size and position
        '''
        cv2.namedWindow("Minimap Debug", cv2.WINDOW_NORMAL)
        cv2.moveWindow("Minimap Debug", 1500, 0)

        cv2.namedWindow("Game Debug View", cv2.WINDOW_NORMAL)
        cv2.moveWindow("Game Debug View", 1280, 700)

    def run(self):

        """#pre_process"""

        self._setting_cv2_map()
        self._connect_window()
        # adjusting display window
        bring_to_front_and_center_origin(self.hwnd)
        self._load_game_resources()

        # process
        self.screen_loop()

    # =================
    # Main Control
    # =================

    def screen_loop(self):
        '''
        Full screen refresh loop
        '''

        try:
            while True:
                # Window handling

                # If window minimized, wait for restore
                if not self._is_window_valid():
                    time.sleep(1)
                    continue

                # Check: is game window in foreground
                is_game_window_foreground = self._is_game_window_foreground()
                if not is_game_window_foreground and self.is_game_window_foreground_last_frame:  # <- Trigger immediately on window focus loss
                    self.keyboard.release_all()
                    self.keyboard.stop_move()
                self.is_game_window_foreground_last_frame = is_game_window_foreground  # Update foreground state

                # Screen capture
                self.frame_bgr = self._scan_full_screen()
                '''
                ==============
                | Data Packet Collection |
                ==============
                '''
                # Poll hotkeys
                self.hotkey_manager.poll()

                # =============
                # @brief   Pause state
                # @detail  Three conditions pause the loop: 1. Window minimized 2. Foreground is not game 3. User paused loop
                # @note    Must run after self.hotkey_manager.poll() to capture hotkeys
                # =============
                if not self.bot_enabled or not is_game_window_foreground:  # Standby during pause
                    time.sleep(0.05)  # Avoid high CPU usage during idle
                    continue

                    # start =time.time()

                # Detect and update data
                self.player_tracking_logic()
                self.HealthDetector()
                self.current_mobs_result = self.MobDetector()
                mini_player_loc = self.MinimapDetector()

                # print(f"Template match draw time: {time.time() - start:.3f}")

                # Data encapsulation
                current_game_state = GameState(
                    player_center_loc=self.player_center_loc,
                    player_hp=self.player_hp,
                    player_mp=self.player_mp,
                    roi_BBOX=self.roi_BBOX,
                    mobs=self.current_mobs_result,
                    mini_player_loc=mini_player_loc,
                )

                '''
                decide_operation ,execute_behavior  -> (str, dict{})
                '''
                try:
                    action_oder, target_info = self.auto_control.run(current_game_state)
                    # print(f"Action: {action_oder} Target: {target_info}")
                except Exception as e:
                    logging.error(f"Exception occurred in auto_control.run: {e}", exc_info=True)
                    continue

                # print(f"Action: {action_states} Target: {target_info}")

                # Transmit to state machine only when action_oder exists and game is in foreground
                if action_oder is not None and is_game_window_foreground:
                    self.action_handler.execute_behavior(action_oder, target_info)

                # Render BBox, Text
                self._render_cv2_view(mini_player_loc, action_oder)
                self._render_minimap_overlay(mini_player_loc)

                '''
                ================
                '''

                # OpenCV Game Debug View display
                # print(f"One while loop elapsed: {time.time() - start:.3f}")
        except Exception as e:
            logging.error(f"Exception occurred in screen_loop: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    # =================
    # Player Detection Logic
    # =================
    def player_tracking_logic(self):
        '''
        Function:
            Controls ROI and full screen scanning logic
        '''
        try:
            if self.player_center_loc is None:
                # Full screen scan
                player_loc = self._locate_player_globally()

                # Guard check
                if player_loc is not None:
                    self.player_center_loc = cent_coord(player_loc, self.my_character_template_size)
                    self.loss_tracking_count = 0  # Reset count on detection
                else:
                    pass
            else:
                # Enter ROI scan
                fund_result = self._locate_player_locally()
                # If not found in ROI, clear pos and ROI box so next cycle reverts to full scan

                if fund_result:
                    self.loss_tracking_count = 0  # Reset count on detection

                else:
                    predicted = self._predict_player_position()  # <- Attempt tracking fallback
                    if not predicted:
                        # Prediction failed (exceeded max tolerance frames), fully clear
                        self.player_center_loc = None
                        self.roi_BBOX = None

            # Compute character bbox for visualization
            if self.player_center_loc is not None:
                # Character bbox coords tuple[tuple[int,int],tuple[int,int]]
                self.role_BBOX = get_bbox_from_center(self.player_center_loc, self.my_character_template_size)


            else:
                # Reset if not found
                self.role_BBOX = None

            # ========
            # Update frame data
            # =======
            if self.player_center_loc is not None:
                self.prev_pcl = self.player_center_loc
                self.prev_role_BBOX = self.role_BBOX
        except Exception as e:
            logging.error(e)

    def _locate_player_globally(self):
        '''
        Function:
            Full screen scan
        return: 
            Origin of matched target
        '''
        try:
            current_frame = cv2.cvtColor(self.frame_bgr, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(current_frame, self.my_character_template_gray, self.method,
                                       mask=self.mask)

            # Character found
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > self.min_threshold:
                logging.info(f"Full screen scan found character at {max_loc}, confidence: {max_val}")
                self.role_score = max_val
                return max_loc
            else:
                logging.info("Full screen scan: character not matched")

        except Exception as e:
            logging.error(e)

    def _locate_player_locally(self):
        '''
        Function:
            Local ROI scan

        return: bool
            True: Found
            False: Not found
        Note:
            Directly updates self.player_center_loc and self.role_BBOX
        '''
        try:

            # Type is tuple(x,y)
            top = max(0, self.player_center_loc[1] - self.roi_top_offset)
            left = max(0, self.player_center_loc[0] - self.roi_left_offset)
            bottom = min(self.frame_size[1], self.player_center_loc[1] + self.roi_bottom_offset)
            right = min(self.frame_size[0], self.player_center_loc[0] + self.roi_right_offset)

            # Calculate ROI bounds
            self.roi_BBOX = BBox(left, top, right, bottom)

            # [!] OpenCV slice expects [y_range, x_range]
            roi_crop_frame = self.frame_bgr[top:bottom, left:right]
            self.roi_crop_frame_gray = cv2.cvtColor(roi_crop_frame, cv2.COLOR_BGR2GRAY)
            matches = cv2.matchTemplate(self.roi_crop_frame_gray, self.my_character_template_gray,
                                        self.method, mask=self.mask)
            _, max_val, _, max_loc = cv2.minMaxLoc(matches)

            if max_val > self.min_threshold:

                # Local coords to global coords: global = local + roi_origin
                player_loc_globally = (max_loc[0] + self.roi_BBOX.x1, max_loc[1] + self.roi_BBOX.y1)

                self.player_center_loc = cent_coord(player_loc_globally, self.my_character_template_size)
                self.role_BBOX = get_bbox_from_center(self.player_center_loc, self.my_character_template_size)

                return True

            else:
                logging.info('ROI scan: character not found')

                return False

        except Exception as e:
            logging.error(e)

    def _predict_player_position(self):
        '''
        Purpose:
            Use previous position to handle brief tracking loss
        '''
        MAX_LOST_FRAMES = 15

        if self.prev_pcl is not None and self.loss_tracking_count < MAX_LOST_FRAMES:
            self.player_center_loc = self.prev_pcl
            if self.prev_roi_BBOX is not None:
                self.roi_BBOX = self.prev_roi_BBOX
            self.loss_tracking_count += 1
            return True
        else:
            # Exceeded tolerance, reset counter
            self.loss_tracking_count = 0
            return False

    # =================
    # Detector: Monsters
    # =================
    def MobDetector(self):
        '''
        Interact with monster detector: send grayscale frame and receive detected monster packet.
        '''
        if self.roi_crop_frame_gray is not None:
            # push data

            mob_results = self.mob_detector.searching_mob(self.roi_crop_frame_gray)

            return mob_results

    # =================
    # Detector: Health
    # =================

    def HealthDetector(self):
        '''
        get:self.player_hp
        '''
        try:
            # Note: update if MP detection logic changes
            self.player_hp, self.player_mp = self.health_dectector.run(self.frame_bgr)

        except Exception as e:
            logging.error(e)

    # =================
    # Detector: Minimap
    # =================
    def MinimapDetector(self) -> tuple[int, int]:
        '''
        WIP
        Interact with minimap detector: send current BGR frame
        return: player position (x, y)
        '''
        mini_player_loc = self.minimap_detector.run(self.frame_bgr)
        return mini_player_loc

    # =================
    # Drawing Functions
    # =================

    def _show_player_loc(self, player_loc):

        cv2.putText(self.frame_bgr, f"Player Pos: {player_loc}", org=(10, 250),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 0, 0), thickness=2)

    def _show_player_action_states(self, action_state):
        cv2.putText(self.frame_bgr, f"State: {action_state}", org=(10, 300),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 0, 0), thickness=2)

    def _show_player_HP(self, HP):
        cv2.putText(self.frame_bgr, f"HP Bar: {int("50")}%", org=(10, 350),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(0, 0, 225), thickness=2)

    def _show_player_MP(self, MP):
        cv2.putText(self.frame_bgr, f"MP Bar: {int("50")}%", org=(10, 400),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(225, 0, 225), thickness=2)

    def _draw_mob(self, mob_results: list):
        """
        Parse monster data and draw bounding boxes
        """
        if mob_results and self.roi_BBOX is not None:
            for mob_name, mob_details in mob_results:

                for detailed in mob_details:
                    x1 = detailed["top_left"][0] + self.roi_BBOX.x1
                    y1 = detailed["top_left"][1] + self.roi_BBOX.y1
                    w, h = detailed["size"]
                    score = detailed["score"]
                    clean_name = re.sub(r'\s*\(\s*\d+\s*\)', '', mob_name)
                    score_text = f"{score:.2f}"
                    clean_name = f"{clean_name} {score_text}"

                    draw_dectection_box(
                        self.frame_bgr,
                        (x1, y1),
                        (x1 + w, y1 + h),
                        label=clean_name, color=(0, 0, 255),
                        top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)

    def _draw_player(self):
        '''
        Draw player bounding box
        '''
        role_name = f"Player {self.role_score:.2f}"
        draw_dectection_box(self.frame_bgr, self.role_BBOX.top_left, self.role_BBOX.bottom_right, label=role_name,
                            top_padding=80, bottom_padding=0, left_padding=0, right_padding=0, color=(219, 112, 147))

    def _draw_player_roi_bbox(self):
        '''
        Draw player ROI bounding box
        '''
        draw_dectection_box(self.frame_bgr, self.roi_BBOX.top_left, self.roi_BBOX.bottom_right, label="Search Area",
                            top_padding=0, bottom_padding=0, left_padding=0, right_padding=0, color=(42, 42, 165))
