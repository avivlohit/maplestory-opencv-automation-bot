import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.config_loader import config 
import interception
import time
from config.config_loader import config
from src.utils.common import get_window_handle_and_rect_by, bring_to_front_and_center_origin
import win32gui
import cv2
import ctypes
import numpy as np
from PIL import ImageGrab
import time
'''
Select coordinates and bounds interactively with mouse ROI selection or direct coordinate input.
'''

ctypes.windll.shcore.SetProcessDpiAwareness(2)


window_name =  config.get("game.title")

hwnd, client_rect = get_window_handle_and_rect_by(window_name)
time.sleep(1)
bring_to_front_and_center_origin(hwnd)
print(hwnd, client_rect)

# Relative coordinates
screen_rect = win32gui.GetClientRect(hwnd)

print(f"screen_rect: {screen_rect}")
# Absolute coordinates
abs_x2, abs_y2 = win32gui.ClientToScreen(hwnd, (screen_rect[2], screen_rect[3]))
x1,y1 = win32gui.ClientToScreen(hwnd, (screen_rect[0], screen_rect[1]))
x2,y2 = win32gui.ClientToScreen(hwnd, (screen_rect[2], screen_rect[3]))
abd_lect = (x1,y1,x2,y2)
current_frame = ImageGrab.grab(bbox=abd_lect)
current_frame = np.array(current_frame)
frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) # Image processing defaults to BGR

# Drag mouse to select template area, press Enter/Space to confirm, c to cancel
roi = cv2.selectROI("Drag to select HP bar ROI, press Enter when done", frame_bgr, showCrosshair=True)

# Direct coordinate input
# x1, y1, x2, y2 = (620, 789, 724, 800)
w = x2 - x1
h = y2 - y1
print(f"Coordinates: x1={x1}, y1={y1}, x2={x2}, y2={y2}")

cropped = frame_bgr[y1:y2, x1:x2]
cv2.imwrite("hp_template.png", cropped)
print("Saved hp_template.png")

cv2.imshow("TEST", frame_bgr)
cv2.waitKey(0)
cv2.destroyAllWindows()
