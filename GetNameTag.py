import tools.get_nametag
import logging
import os
import sys
import ctypes 
'''
Temporary script.
Launches the module to capture the character name tag for coordinate template matching.
'''
    #=================
    # OS Administrator Privileges
    #=================
def is_admin():
    """Check if currently running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Rerun current script with administrator privileges."""

    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)


if __name__ == "__main__":

    #--- Administrator privileges
    if not is_admin():
        run_as_admin()
        sys.exit()
    try:
        run = tools.get_nametag.GetRoleImg()
        run.run()
    except Exception as e:
        logging.exception(f"Unexpected exception: {e}")
