"""
Monitor topology and resolution detection.
Queries and parses xrandr output to discover connected displays, geometries, and orientations.
"""

import os
import re
import subprocess
from .browser import get_x_env

def get_connected_monitors():
    """
    Query xrandr for connected outputs and their configurations.
    Returns list of monitor dictionaries.
    """
    env = get_x_env()
    try:
        res = subprocess.run(["xrandr", "--query"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        output = res.stdout
    except Exception:
        return []

    monitors = []
    current_monitor = None

    for line in output.splitlines():
        if " connected" in line:
            parts = line.split()
            name = parts[0]
            is_primary = "primary" in parts
            
            # Match resolution and position e.g. 1920x1080+0+0
            res_pos_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
            
            # Match rotation
            rot_match = re.search(r'\s+(left|right|inverted)\s+', line)
            rotation = rot_match.group(1) if rot_match else "normal"

            orig_w, orig_h = 1920, 1080
            pos_x, pos_y = 0, 0
            if res_pos_match:
                orig_w = int(res_pos_match.group(1))
                orig_h = int(res_pos_match.group(2))
                pos_x = int(res_pos_match.group(3))
                pos_y = int(res_pos_match.group(4))

            # Calculate dimensions after rotation
            if rotation in ['left', 'right']:
                width = orig_h
                height = orig_w
            else:
                width = orig_w
                height = orig_h

            current_monitor = {
                "name": name,
                "primary": is_primary,
                "orig_width": orig_w,
                "orig_height": orig_h,
                "width": width,
                "height": height,
                "pos_x": pos_x,
                "pos_y": pos_y,
                "rotation": rotation,
                "modes": []
            }
            monitors.append(current_monitor)
        elif current_monitor and re.match(r'^\s+(\d+x\d+)', line):
            mode_match = re.match(r'^\s+(\d+x\d+)', line)
            if mode_match:
                current_monitor["modes"].append(mode_match.group(1))

    return monitors
