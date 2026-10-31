import cv2
import numpy as np
import win32gui
import win32con
from src.utils.boxes import BBox
from pathlib  import Path

import yaml
def get_mask(img, ignore_pixel_color):
    '''
    Generate foreground mask: pixels matching ignore_pixel_color are ignored
    '''
    mask = np.all(img == ignore_pixel_color, axis=2).astype(np.uint8) * 255
    mask = cv2.bitwise_not(mask)

    return mask


def get_window_handle_and_rect_by(title_name:str)-> tuple[int, tuple[int, int, int, int]]:
    """Get window handle and window absolute coordinates on screen."""

    hwnd = win32gui.FindWindow(None,title_name)
    if not hwnd:
        return None

    # Get window absolute coordinates: returns (left, top, right, bottom)
    window_rect = win32gui.GetWindowRect(hwnd)

    return hwnd, window_rect

def bring_to_front_and_center_origin(hwnd:int):
    '''
    Organize window position
    Bring window to foreground and initialize position at (0, 0)
    '''
    try:
        # Restore normal size if window is minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Bring window to foreground
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f"Failed to bring window to foreground: {e}")

    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)


def cent_coord(global_loc:tuple[int,int],template_size:tuple[int,int]) -> tuple[int,int]: 
    '''
    Calculate center point of location
    Input: Target global coordinate (top-left reference) x, y; template dimensions [width, height]
    Input is (x, y); Output is (x, y)
    '''
    center_w = int(global_loc[0]+(template_size[0]//2))
    center_h = int(global_loc[1]+(template_size[1]//2))
    return center_w,center_h


def get_bbox_from_center(cen_loc:tuple[int,int],template_size:tuple[int,int]) -> tuple[tuple[int,int],tuple[int,int]]:
    '''
    Calculate bbox from center point
    Input: Center coordinates (x, y), template dimensions [w, h]
    Output: BBox object (x1, y1, x2, y2)
    '''
    # Unpack
    cx, cy = cen_loc
    t_w, t_h = template_size
    # Calculate bbox
    x1 = cx - t_w // 2
    y1 = cy - t_h // 2
    x2 = cx + t_w // 2
    y2 = cy + t_h // 2

    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)

def convert_img2xy(img:np.ndarray)->tuple[int,int] : 
    # Convert image shape (height, width) to (width, height) (x, y)
    y,x = img.shape[:2]
    return (x,y)


def draw_dectection_box(frame,left_top,right_bottom,label="Target",color=(0,255,0),thickness=2,
                        top_padding=0, bottom_padding=0, left_padding=0, right_padding=0):
    '''Draw detection ROI box: frame, top-left, bottom-right, label, color, thickness, paddings'''

    # Box padding adjustment
    left_top = (left_top[0] - left_padding, left_top[1] - top_padding)
    right_bottom = (right_bottom[0] + right_padding, right_bottom[1] + bottom_padding)

    cv2.rectangle(frame, left_top, right_bottom, color, thickness)

    cv2.putText(
        frame, 
        str(label), 
        (left_top[0], left_top[1] - 10), # Text positioned slightly above top-left of box
        cv2.FONT_HERSHEY_SIMPLEX, 
        0.5, 
        color, 
        2
    )
    return frame


def BGR2Binary(img: np.ndarray) -> np.ndarray:
    '''Convert BGR color image to grayscale, then perform Otsu thresholding to binary'''

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return binary
