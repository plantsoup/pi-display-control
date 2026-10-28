"""
Monitor topology and resolution detection.
Queries and parses xrandr output (with Linux DRM sysfs fallback) to discover
physically connected displays, geometries, and orientations.
"""

import os
import re
import glob
import subprocess
from .browser import get_x_env

_VIRTUAL_OUTPUT_PREFIXES = ("NOOP", "VIRTUAL", "DUMMY", "WRITEBACK")


def _is_virtual_output(name):
    if not name:
        return True
    upper = name.upper()
    return any(upper.startswith(prefix) for prefix in _VIRTUAL_OUTPUT_PREFIXES)


def _detect_drm_connected_monitors():
    """
    Fallback monitor detection via Linux /sys/class/drm when X11/xrandr is unavailable.
    Only returns connectors whose hardware status is strictly 'connected'.
    """
    drm_root = "/sys/class/drm"
    if not os.path.isdir(drm_root):
        return []

    monitors = []
    for status_path in sorted(glob.glob(os.path.join(drm_root, "card*-*", "status"))):
        conn_dir = os.path.dirname(status_path)
        folder_name = os.path.basename(conn_dir)
        # Strip 'card0-' or 'card1-' prefix -> e.g. 'HDMI-A-1'
        short_name = re.sub(r"^card\d+-", "", folder_name)
        if _is_virtual_output(short_name):
            continue

        try:
            with open(status_path, "r", encoding="utf-8") as f:
                status_val = f.read().strip().lower()
        except Exception:
            continue

        if status_val != "connected":
            continue

        modes = []
        orig_w, orig_h = 1920, 1080
        modes_path = os.path.join(conn_dir, "modes")
        if os.path.exists(modes_path):
            try:
                with open(modes_path, "r", encoding="utf-8") as f:
                    for m_line in f:
                        m_clean = m_line.strip()
                        if re.match(r"^\d+x\d+$", m_clean):
                            modes.append(m_clean)
                if modes:
                    w_str, h_str = modes[0].split("x")
                    orig_w, orig_h = int(w_str), int(h_str)
            except Exception:
                pass

        monitors.append({
            "name": short_name,
            "primary": len(monitors) == 0,
            "orig_width": orig_w,
            "orig_height": orig_h,
            "width": orig_w,
            "height": orig_h,
            "pos_x": 0,
            "pos_y": 0,
            "rotation": "normal",
            "modes": modes,
            "connected": True
        })

    return monitors


def get_connected_monitors():
    """
    Query xrandr for physically connected outputs and their configurations.
    Returns list of connected monitor dictionaries (empty list if no displays are attached).
    """
    env = get_x_env()
    xrandr_ok = False
    output = ""
    try:
        res = subprocess.run(
            ["xrandr", "--query"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if res.returncode == 0 and res.stdout:
            xrandr_ok = True
            output = res.stdout
    except Exception:
        xrandr_ok = False

    if not xrandr_ok:
        return _detect_drm_connected_monitors()

    monitors = []
    current_monitor = None

    for line in output.splitlines():
        if " connected" in line:
            parts = line.split()
            name = parts[0]
            if _is_virtual_output(name):
                current_monitor = None
                continue

            is_primary = "primary" in parts

            # Match resolution and position e.g. 1920x1080+0+0
            res_pos_match = re.search(r"(\d+)x(\d+)\+(\d+)\+(\d+)", line)

            # Match rotation
            rot_match = re.search(r"\s+(left|right|inverted)\s+", line)
            rotation = rot_match.group(1) if rot_match else "normal"

            orig_w, orig_h = 1920, 1080
            pos_x, pos_y = 0, 0
            if res_pos_match:
                orig_w = int(res_pos_match.group(1))
                orig_h = int(res_pos_match.group(2))
                pos_x = int(res_pos_match.group(3))
                pos_y = int(res_pos_match.group(4))

            # Calculate dimensions after rotation
            if rotation in ["left", "right"]:
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
                "modes": [],
                "connected": True
            }
            monitors.append(current_monitor)
        elif line and not line[0].isspace():
            current_monitor = None
        elif current_monitor and re.match(r"^\s+(\d+x\d+)", line):
            mode_match = re.match(r"^\s+(\d+x\d+)", line)
            if mode_match:
                current_monitor["modes"].append(mode_match.group(1))

    return monitors
