import os
from pathlib import Path
import cv2
import numpy as np
'''
Function: Inspect image HSV color range
'''

#path
current_dir = Path(__file__).parent
template_path = current_dir.parent / "img" / "health_stuff" / "mp_template.png"
# Load template
img = cv2.imread(template_path, cv2.IMREAD_COLOR)
# Convert to HSV
hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# Calculate min and max for H, S, V across image
h, s, v = cv2.split(hsv_img)
print(f"H range: {np.min(h)} ~ {np.max(h)}")
print(f"S range: {np.min(s)} ~ {np.max(s)}")
print(f"V range: {np.min(v)} ~ {np.max(v)}")
