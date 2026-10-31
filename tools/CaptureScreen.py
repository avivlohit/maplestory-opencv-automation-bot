import cv2
import numpy as np
import time
import threading
import keyboard
import win32gui
import pyautogui
from PIL import ImageGrab
import ctypes

# Must execute before win32gui / ImageGrab / pyautogui calls
ctypes.windll.shcore.SetProcessDpiAwareness(2)


class WindowCapureTool:
    def __init__(self):
        self.running = True
        self.output_folder = "processed_screenshots"

    def run(self):
        # Bind hotkeys
        keyboard.add_hotkey('f2', self.grab_screenshot)
        keyboard.add_hotkey('f3', self.stop)

        print("Controls: Press F2 to capture client window screenshot, F3 to exit\n")

        # Background thread continuously updates coordinates
        threading.Thread(target=self._print_mouse_position, daemon=True).start()

        # Main loop waiting for exit signal
        while self.running:
            time.sleep(0.1)

        print("[Program safely closed]")
        keyboard.unhook_all()  # Unhook all hotkeys
        cv2.destroyAllWindows()

    def _get_client_screen_bbox(self, hwnd):
        """
        Unified client region coordinate calculation:
        Returns client area screen absolute coordinates (x1, y1, x2, y2).
        Matches coordinate system used in main program.
        """
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        x1, y1 = win32gui.ClientToScreen(hwnd, (left, top))
        x2, y2 = win32gui.ClientToScreen(hwnd, (right, bottom))
        return x1, y1, x2, y2

    def grab_screenshot(self):
        '''Capture client area screenshot of foreground window (excluding title bar and borders)'''

        hwnd = win32gui.GetForegroundWindow()
        real_bbox = self._get_client_screen_bbox(hwnd)

        screenshot = ImageGrab.grab(bbox=real_bbox)
        frame = np.array(screenshot)
        screenshot = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # save the screenshot
        filename = f"{self.output_folder}/screenshot_{int(time.time())}.png"
        cv2.imwrite(filename, screenshot)
        print(f"Screenshot captured and saved to {filename}")
        print(f"Screenshot dimensions (H, W): {screenshot.shape[:2]}  <- Valid client relative coordinate bounds")

        cv2.imshow("TEST", screenshot)
        cv2.waitKey(0)

    def stop(self):
        """Safe exit"""
        print("\n>>> Received F3 exit signal... <<<")
        self.running = False

    def _print_mouse_position(self):
        """Continuously update mouse coordinate display in background thread using client relative coordinates"""
        print("--- Tracking mouse coordinates ---", end="\r")
        try:
            while self.running:
                hwnd = win32gui.GetForegroundWindow()
                try:
                    cx1, cy1, cx2, cy2 = self._get_client_screen_bbox(hwnd)

                    mouse_x, mouse_y = pyautogui.position()

                    rel_x = mouse_x - cx1
                    rel_y = mouse_y - cy1

                    # Check if mouse is within client bounds
                    in_range = (0 <= rel_x <= (cx2 - cx1)) and (0 <= rel_y <= (cy2 - cy1))
                    tag = "OK" if in_range else "Out of client bounds"

                    print(
                        f"\rClient Rel -> X: {rel_x:4d}, Y: {rel_y:4d} "
                        f"| Screen Abs X: {mouse_x:4d}, Y: {mouse_y:4d} [{tag}]    ",
                        end="", flush=True
                    )
                except Exception:
                    print("--- Please move mouse into target window ---                             ", end="\r")

                time.sleep(0.1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    tool = WindowCapureTool()
    tool.run()
