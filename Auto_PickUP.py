import interception
import threading
import keyboard
import time
import os
import win32gui
import ctypes
import sys
import win32con
import logging
from config.config_loader import config

"""
Semi-automated auto-loot script
Triggers the pick-up key whenever directional keys (Up/Down/Left/Right) are active.
"""

'''Parameters'''
AUTO_PICK_DELAY = 0.25
GAME_TITLE = config.get("game.title", "MapleStory")
PICK_UP_KEY = config.get("keyboard.pick_up", "z")  # Default pick-up key
PICK_UP_COOLDOWN = 0.05  # Cooldown between pick-ups in seconds

class Bat:
    def __init__(self):
        interception.auto_capture_devices(keyboard=True, mouse=False)
        self.MapleStory_hhwnd = None

        # Lock
        self._pick_up_lock = threading.Lock()
        self._lock = threading.Lock()
        # Flag
        self._pick_up = False
        self.is_picking_up = True

        self.pick_event = threading.Event()

    # ===================
    # Key command module
    # ===================
    def _pick_up_command(self, key):
        try:
            interception.key_down(key)
            time.sleep(PICK_UP_COOLDOWN)
        except Exception:
            pass
        finally:
            interception.key_up(key)
            self._pick_up = False

    def enable_pick_up(self):
        current_hwnd = win32gui.GetForegroundWindow()
        # Restrict command to MapleStory game window
        if current_hwnd != self.MapleStory_hhwnd:
            return

        if not self.is_picking_up:
            return
        
        with self._pick_up_lock:
            if not PICK_UP_KEY:
                return
            self._pick_up = True
        threading.Thread(target=self._pick_up_command, args=(PICK_UP_KEY,), daemon=True).start()

    def toggle_pick_up(self):
        '''Toggle pick-up mode'''
        if self.is_picking_up:
            self.is_picking_up = False
            print("Auto-pickup disabled")
        else:
            self.is_picking_up = True
            print("Auto-pickup enabled")

    def exit_process(self):
        print("Exiting...")
        keyboard.unhook_all()
        os._exit(0)

    # ===================
    # Game window management
    # ===================
    def is_MapleStory_window(self):
        try:
            MapleStory_hhwnd = win32gui.FindWindow(None, GAME_TITLE)
            logging.info(f"Found window '{GAME_TITLE}', handle: {MapleStory_hhwnd}")
            return MapleStory_hhwnd
        except Exception as e:
            logging.warning(f"Window '{GAME_TITLE}' not found, error: {e}")
            return False
        
    def bring_to_front_and_center_origin(self, hwnd: int):
        '''Bring window to foreground and reset to origin'''
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"Failed to bring window to foreground: {e}")

        win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

    def _pre_loading(self):
        self.MapleStory_hhwnd = self.is_MapleStory_window()

    def run(self):
        self._pre_loading()
        if self.MapleStory_hhwnd:
            self.bring_to_front_and_center_origin(self.MapleStory_hhwnd)

        print('=' * 20)
        print("F2: Toggle Auto-Pickup\nF3: Exit Program")
        print('=' * 20)

        # Hotkeys
        keyboard.add_hotkey('f2', self.toggle_pick_up)
        keyboard.add_hotkey('f3', self.exit_process)
        keyboard.add_hotkey('left', self.enable_pick_up)
        keyboard.add_hotkey('right', self.enable_pick_up)
        keyboard.add_hotkey('up', self.enable_pick_up)
        keyboard.add_hotkey('down', self.enable_pick_up)
        keyboard.wait()


def is_admin():
    """Check if script has administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    """Relaunch script with administrator privileges"""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

if __name__ == "__main__":
    if not is_admin():
        run_as_admin()
        sys.exit()

    run = Bat()
    run.run()
