import win32gui
import win32process
'''
Function: List all window handles (HWND), process IDs (PID), and window titles.
'''

def list_windows():
  print("=" * 60)
  print(f"{'ID':<5} | {'HWND':<10} | {'PID':<6} | {'Window Title'}")
  print("=" * 60)

  windows = []

  def enum_handler(hwnd, lParam):
    # Capture only visible windows with non-empty titles
    if win32gui.IsWindowVisible(hwnd):
      title = win32gui.GetWindowText(hwnd)
      if title.strip():  # Exclude empty titles
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        windows.append((hwnd, pid, title))
    return True

  win32gui.EnumWindows(enum_handler, None)

  # Print window list
  for idx, (hwnd, pid, title) in enumerate(windows):
    print(f"{idx:<5} | {hwnd:<10} | {pid:<6} | {title}")

  print("=" * 60)



if __name__ == "__main__":
  list_windows()
