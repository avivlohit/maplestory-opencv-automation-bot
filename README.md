## Live Preview

<table>
  <tr>
    <td align="center">
      <img src="./assets/log_img.png" width="400">
    </td>
    <td align="center">
      <img src="./assets/log_img_2.gif" width="400">
    </td>
  </tr>
</table>

>**Disclaimer**
>
> This project is intended solely for personal study of Python computer vision and automation testing exchange.<br>Please use it in compliance with the game's terms of service.

---

## Current Features (WIP)

| Feature | Description |
| :--- | :--- |
| **Auto Movement** | Horizontal movement on platforms<br>Vertical movement (ropes/ladders)<br>Obstacle jumping (requires configured jump points) |
| **Auto Mob Tracking** | Patrol platforms searching for mobs<br>If no mobs are found within a timeout, navigate via vertical channels to a new platform |
| **Auto Combat** | Supports basic attack<br>Supports AOE (Area of Effect) attacks<br>Supports jump-attacks (e.g., Night Lord / Assassin jump-shot) |
| **Auto Pick-up** | Automatically triggers pick-up keystrokes while moving |
| **Auto Potion** | HP potion consumption<br>MP potion consumption |
| **Unstuck Recovery** | If stationary for a period, triggers random walk/jump<br>Finds and returns to the nearest platform |
| **Action Points** | Character triggers actions at specific coordinates during navigation (requires configuration) |

---
### Development / Test Environment
* Screen Resolution (Native): 2560 x 1600
* DPI Scaling: 125%
* Differing environments or display settings may lead to low detection accuracy or misaligned capture regions.

---

## Usage

#### I. Install Environment & Dependencies
```bash
pip install -r requirements.txt
```

#### II. Generate Character Name Tag:
* Launch the game and run `GetNameTag.py`. Find a clean scene/background and press `Z` to capture your character's name tag for template matching.
* Character name tag snapshots are saved in the `img/nametag` directory.

<table>
  <tr>
    <td align="center">
      <img src="./assets/NameTag_demo.png" width="200"><br>
      <em>Press 'Z' to capture once the red bounding box focuses properly</em>
    </td>
    <td align="center">
      <img src="./assets/NameTag_demo_2.png" width="200"><br>
      <em>Successful output yields the character's background-removed name tag</em>
    </td>
  </tr>
</table>

#### III. Record Movement Paths:
* Navigate to `./config/config_data.yaml` and set the target map in `quickly_choice_map`.
* Enter the game, set the game window size to `1366x768`, and launch `OperationLogger.py` to record `platform points` and `vertical movement channels`.

<p align="center">
  <img src="./assets/OperationLogger_demo.png" width="200"><br>
  <em>Drawn movement channels displayed on the minimap</em>
</p>

#### IV. Launch Bot:
* Ensure your character is already located on the corresponding game map.
* Run `main.py` (with administrator privileges if required).
* Default hotkeys: `F9` to Pause / Resume; `F12` to Exit.

---

## Settings & Configuration

* **Potion Settings**
  * Path: `./config/config_default.yaml`
  * `Value`: percentage threshold (0 - 100).
  * 3 stages configured by default; dynamically loaded, allowing additional thresholds as needed.

<p align="center">
  <img src="./assets/setting-1.png" width="300">
</p>

* **Combat Settings**
  * `is_Night_Lord`: Jump-shot toggle for Night Lords / Assassins or whenever jump-attacking is needed.
  * `enable_AOE`: Toggle for enabling Area-of-Effect attacks.
  * `AOE_threshold`: Mob count threshold required to trigger AOE skills.
  * `attack_range`: Character attack range; targets within this range trigger attacks.
  * `mob_min_threshold`: Template matching confidence threshold for mobs. Adjust as needed: too high might miss mobs, too low may cause phantom triggers and whiffing attacks.
  * `role_min_threshold`: Threshold for character detection. Usually does not need modification once the character NameTag is properly set up.
  * `roi_offset`: Bounding box offset size for Region of Interest (ROI). Mob detection only runs within this ROI. Excessively large ROIs impact performance.

<p align="center">
  <img src="./assets/setting-combat-1.png" width="300">
</p>
<p align="center">
  <img src="./assets/setting-combat-2.png" width="300">
</p>

* **Input Control Settings**
  * Uses the third-party library `interception` for hardware-level keystrokes. Key codes are straightforward.
  * To inspect key values, test them using `./tools/keyboard_check.py`.

<p align="center">
  <img src="./assets/setting-horkey-1.png" width="300">
</p>

* **Map Settings**
  * Path: `./config/config_data.yaml`
  * Set `quickly_choice_map` to the active map name.
  * Under the `map` section, configure mob template matching lists corresponding to each map.

<p align="center">
  <img src="./assets/setting-map-1.png" width="300">
</p>

* **Minimap Waypoint Configuration**
  * Path: `./img/mini_map/[Map_Name]/[Map_Name].yaml`
  * To add new map templates, source them from sites such as `maplestory.wiki`.

<table>
  <tr>
    <td align="center">
      <img src="./assets/setting-4.png" width="300"><br>
      <em>Waypoints and paths plotted via the recording script</em>
    </td>
    <td align="center">
      <img src="./assets/setting-3.png" width="300"><br>
      <em>Format of recorded coordinates in YAML</em>
    </td>
  </tr>
</table>

* **Waypoint Recording Guide**
  * Run `OperationLogger.py` in the root directory to record paths.
  * Alternatively, edit the YAML files under `img/mini_map/` manually.

| Hotkey | Description | Note |
| :--- | :--- | :--- |
| **F1** | Save behavior coordinates to YAML | Exports all recorded actions to config file |
| **F2** | Exit program | Safely quit logger |
| **F4** | Record point: `Walk` | Standard movement point |
| **F5** | Record point: `Rope` | Vertical ladder / rope climbing point |
| **F6** | Record point: `Jump` | Action point triggering jump |
| **F7** | Record point: `JumpDown` | Action point triggering down-jump |
| **-** | Record point: `M_LEFT` | Micro-movement left (~4 pixels) |
| **+** | Record point: `M_RIGHT` | Micro-movement right (~4 pixels) |

---

## Dev Notes

>[LEARNING] **Template Matching**: Tested slicing, masking, and other techniques to improve precision, but many added significant computational overhead without noticeable accuracy gains. Ultimately, using a thread pool was simpler and more effective. During testing without filtering algorithms, match locations exploded, and drawing bounding boxes caused CTD (crash to desktop) due to high load.

>[NOTE] **Automated Decision Flow**: Health Check -> Combat Check -> Platform Patrol for Mobs -> Timeout (No mobs found) -> Unstuck Check -> Platform Vertical Path Search -> Move to Next Platform.<br>Unstuck Logic: 1. If not on a platform or rope, identify and navigate to the nearest platform.

>[NOTE] **Pixel Offset**: Each game restart exhibits a pixel offset of X: 0~2, Y: 0~2. Currently addressed by relaxing tolerances.

>[DONE] **Map Boundary Detection**: Older versions counted missed detections when character ROI was lost; upon reaching a threshold, random walking was triggered. Now migrated to minimap + coordinate platforming for left/right boundary detection.

>[TODO -> DONE] **Mob Hunting Logic**: Switched to computing positions from character minimap coordinates, which is significantly better than random patrol and avoids heavy character screen coordinate extraction.

>[TODO -> DONE] **X/Y Movement**: Y-axis movement still needs optimization. Detailed actions are all bound to minimap X/Y, including using the single Y-axis to monitor climbing status.

>[ISSUE -> FIX] **Health Monitoring**: Screen mismatch caused pixel reading errors. Flashing HP bar read as 0, repeatedly triggering potions. Fixed with abnormal value filtering and potion cooldowns.

>[ISSUE -> FIX] **Health Module DPI Issue**: Hardcoded HP detection regions broke when DPI scaling changed. Replaced with template matching for dynamic coordinate initialization.

>[TODO -> DONE] **Unstuck Return**: When exceeding boundaries, return to the nearest platform (large Y discrepancies need further handling).

>[ISSUE -> FIX] **Minimap Misalignment**: OpenCV minimap didn't align with the actual game minimap. Cause: `cv2.findNonZero` points were averaged, skewing coordinates. Resolved using `cv2.findContours` (`cv2.RETR_EXTERNAL`, `cv2.CHAIN_APPROX_SIMPLE`) to extract only the largest outer contour.

>[ISSUE -> FIX] **Vertical Climbing Key Jam**: Rope movement had an issue with the UP key getting stuck. Climbing down had similar issues; mostly resolved now.

<p align="center">
  <img src="./assets/issue-minimap.png" width="300">
  <br>
  <em>cv2 bounding box misaligned with original map (Fixed)</em>
</p>

>[TODO -> DONE] **Template Matching Optimization**: Migrated to template matching supporting MASKs to filter backgrounds. Applied to mob templates and character name tags.

>[TODO] **Action Points**: Adding more action point types (jump left, jump right, jump down) in the `PathfindState` class. Single jumps added; multi-jump chains still pending.

>[TODO -> DONE] **AutoControl Refactoring**: Previous logic used heavy flags and nested IF statements, making maintenance difficult. Refactored FSM into cleaner state handlers and a command dispatcher.

>[FIX] **Combat Function `_fk_that_mob`**: Mixing screen-space character coordinates with minimap coordinates caused conflicting behaviors. Resolved.

>[UPDATE] **Removed `JumpState` FSM**: Jump point evaluations were integrated directly into horizontal and vertical movement logic, making `JumpState` redundant.

---

## Tools

| File | Core Purpose | Notes |
| :--- | :--- | :--- |
| `Auto_PickUP.py` | Auto loot script | Automatically triggers loot key whenever directional keys (Up/Down/Left/Right) are active |
| `GetNameTag.py` | Capture character name tag | Used to extract character name tag for template matching. Run in a clean scene and press `Z` |
| `CaptureScreen.py` | Coordinate display & screenshot | Calculates screen coordinates vs window client coordinates |
| `OperationLogger.py` | Minimap waypoint recorder | Records platform points and channels. Output saved under `img/mini_map/[Map_Name]/`. Configure `quickly_choice_map` in `config_data.yaml` first |
| `CocoBeater.py` | Coconut harvesting script | Farming script for gathering coconuts. Channel switching stops at channel 60 |
| `keyboard_check.py` | Key code inspector | Displays key names from the `keyboard` package for easy config keybinding |

---

## Tech Stack

* **Window Capture (Win32 API + Pillow)**:
  * Uses `win32gui` to obtain game window handle (`hwnd`) and client rect (`GetClientRect` / `ClientToScreen`).
  * Combined with `ImageGrab` (mss/Pillow) for high-performance window capture, converted to OpenCV BGR format.
* **Template Matching**:
  * **Grayscale & Binary Preprocessing**: Converts captures and templates to grayscale, using `cv2.threshold` (OTSU) to reduce noise and enhance edges.
  * `TM_CCORR_NORMED`: Normalized cross-correlation supporting alpha masks; sensitive to brightness.
  * `TM_CCOEFF_NORMED`: Normalized correlation coefficient; subtracts mean and divides by standard deviation to reduce brightness and contrast fluctuations.
  * **NMS (Non-Maximum Suppression)**:
    * Cleans up redundant overlapping bounding boxes, reducing drawing load and stabilizing mob targeting.
* **Hardware & Input Control**:
  * `interception`: Driver-level / hardware keystroke injection capable of bypassing standard game hooks.
  * `keyboard`: Simple user-space input library (used for listener/testing tools).
  * `win32gui`: Native Windows API for window management and handle manipulation.
* **Concurrency**:
  * `ThreadPoolExecutor` from `concurrent.futures` to parallelize multi-template mob matching.
