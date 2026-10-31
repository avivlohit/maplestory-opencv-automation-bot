# GMS Classic World Migration & Calibration Guide

This guide walks you through getting this bot running on **Global MapleStory (GMS) Classic World**.

---

## 1. Prerequisites & Environment Setup

1. **Python Dependencies**:
   Install the required libraries in your Python environment:
   ```bash
   pip install -r requirements.txt
   ```
2. **Interception Driver**:
   The bot uses `interception-python` for driver-level keystroke emulation (which bypasses standard Windows message hook detection). Ensure the Interception driver is installed on your Windows system:
   - Download the Interception driver installer from command-line tools.
   - Run `install-interception.exe /install` in an Administrator terminal and reboot your PC if prompted.

---

## 2. Configuration Adjustments

Open [`config/config_default.yaml`](file:///c:/Users/avivl/PycharmProjects/maplestory-opencv-automation-bot/config/config_default.yaml):

### 2.1 Verify Game Window Title
```yaml
game:
  title: "MapleStory"  # Or your exact window title, e.g., "MapleStory Worlds"
```
> [!TIP]
> Run `python tools/PrintAllWindows.py` while your game is open to confirm the exact title string.

### 2.2 Minimap Alignment
```yaml
minimap:
  crop_offset: [6, 72]  # [x, y] pixel offset from top-left of the game window
```
If the minimap on GMS Classic is located elsewhere or has a slightly different border, adjust `crop_offset` so that the crop aligns with the minimap interior.

### 2.3 Health & Mana Bar Coordinates
```yaml
health_detector:
  hp_bar_loc: [475, 750, 631, 760]  # [x1, y1, x2, y2]
  mp_bar_loc: [643, 750, 799, 760]  # [x1, y1, x2, y2]
```
- Open your game client (windowed mode, recommended: 1366x768 or your preferred resolution).
- Run `python tools/CaptureScreen.py` or inspect a screenshot to determine the exact `[x1, y1, x2, y2]` box of your red HP and blue MP bars.
- If your UI has slightly different colors, test the color range using `python tools/HSV_check.py`.

---

## 3. Creating Your In-Game Assets

### 3.1 Character Name Tag (Mandatory)
Player tracking relies on template matching your character's nameplate:
1. Log into your character in GMS Classic World.
2. Stand in a clear area without mobs or busy backgrounds behind your nameplate.
3. Run:
   ```bash
   python GetNameTag.py
   ```
4. When the capture preview locks onto your nameplate, press **`Z`** to take the snapshot.
5. The processed template is saved to `img/nametag/MyRoleNameTag.png`.

### 3.2 Mob Sprites & Map Waypoints
- Select your hunting map in [`config/config_data.yaml`](file:///c:/Users/avivl/PycharmProjects/maplestory-opencv-automation-bot/config/config_data.yaml) via `quickly_choice_map` (e.g. `The_Burnt_Land_I`).
- Verify the mob sprites inside `img/map/<Map_Name>/` match the GMS Classic sprites (transparent background PNGs). If needed, download official sprites from [MapleStory Wiki](https://maplestory.wiki).
- To map out paths and platforms for a new map, launch:
   ```bash
   python OperationLogger.py
   ```
   Use **F4** (Walk), **F5** (Rope/Ladder), **F6** (Jump), and **F1** to export the coordinates to the map's YAML file.

---

## 4. Running the Bot

Run `main.py` with Administrator privileges:
```bash
python main.py
```
- **F9**: Pause / Resume bot automation.
- **F12**: Gracefully exit the bot.
