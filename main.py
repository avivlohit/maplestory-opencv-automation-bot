import ctypes
# Force Python process to recognize actual screen DPI pixels to avoid cropped capture bounds
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass
from src.engine.GameBot import GameBot
import src.utils.logger as logger
import logging
import os
import sys

def is_admin():

    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():

    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)


if __name__ == "__main__":
    try:
        # Initialize logging
        logger.setup_logging()
        #--- Administrator privileges
        if not is_admin():
            run_as_admin()
            sys.exit()
        try:
            run = GameBot()
            run.run()
        except Exception as e:
            logging.exception(f"Unexpected exception: {e}")
        except KeyboardInterrupt:
            logging.info("Interrupted by 'Ctrl+C'")
            logging.info("Shut down cleanly")

    except Exception as e:
        logging.exception(f"Unexpected exception in main.py: {e}")
