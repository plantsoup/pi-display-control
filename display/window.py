"""
Window management and positioning.
Uses xdotool to locate and reposition Chromium windows on target monitors.
"""

import time
import shutil
import subprocess
from .browser import get_x_env

def get_xdotool_windows():
    """Retrieve list of existing Chromium window IDs"""
    env = get_x_env()
    if not shutil.which("xdotool"):
        return []
    try:
        res = subprocess.run(["xdotool", "search", "--class", "chromium"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return [w.strip() for w in res.stdout.strip().splitlines() if w.strip()]
    except Exception:
        pass
    return []

def position_window(existing_windows, x, y, width, height, max_attempts=8):
    """Wait for new Chromium window and position/resize it with xdotool"""
    env = get_x_env()
    if not shutil.which("xdotool"):
        return False

    existing_set = set(existing_windows)
    for _ in range(max_attempts):
        time.sleep(0.5)
        current = get_xdotool_windows()
        new_windows = [w for w in current if w not in existing_set]
        if new_windows:
            target_id = new_windows[0]
            try:
                subprocess.run(["xdotool", "windowmove", target_id, str(x), str(y)], env=env, stderr=subprocess.DEVNULL)
                subprocess.run(["xdotool", "windowsize", target_id, str(width), str(height)], env=env, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
    return False
