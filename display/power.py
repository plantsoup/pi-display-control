"""
Screen power management, blanking, waking, and monitor orientation controls.
Supports dynamic rotation options and startup default orientation persistence.
"""

import os
import time
import shutil
import subprocess
from .browser import get_x_env, kill_chromium
from .monitors import get_connected_monitors
from .manager import start_display, DEFAULT_AUTODARTS_URL, DEFAULT_AUTODARTS_URL2
from .config import (
    load_display_config,
    save_display_config,
    get_monitor_rotation,
    set_default_rotation,
    VALID_ROTATIONS,
    ROTATION_METADATA
)

def _set_display_power(power_on=True):
    """Attempt hardware display power control via vcgencmd without blocking on sudo password"""
    val = "1" if power_on else "0"
    vcgen = shutil.which("vcgencmd") or ("/usr/bin/vcgencmd" if os.path.exists("/usr/bin/vcgencmd") else None)
    if not vcgen:
        return
    env = get_x_env()
    try:
        subprocess.run(["sudo", "-n", vcgen, "display_power", val], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    try:
        subprocess.run([vcgen, "display_power", val], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def blank_screen():
    """Power off screens and terminate Chromium"""
    env = get_x_env()

    # Kill Chromium
    kill_chromium("both")

    # Raspberry Pi hardware blanking
    _set_display_power(power_on=False)

    # Turn off outputs via xrandr
    if shutil.which("xrandr"):
        monitors = get_connected_monitors()
        for m in monitors:
            subprocess.run(["xrandr", "--output", m["name"], "--off"], env=env, stderr=subprocess.DEVNULL)

    return True, "Display blanked successfully"

def wake_screen(url1="", url2=""):
    """
    Power on screens, restore display configuration according to saved defaults,
    and restart Chromium.
    """
    env = get_x_env()

    # Hardware power on
    _set_display_power(power_on=True)

    # Retrieve persistent default rotations
    rot1 = get_monitor_rotation("1", default="left")
    rot2 = get_monitor_rotation("2", default="right")

    # Restore xrandr outputs using saved defaults
    if shutil.which("xrandr"):
        monitors = get_connected_monitors()
        if len(monitors) >= 2:
            m1 = monitors[0]
            m2 = monitors[1]
            mode1 = m1["modes"][0] if m1.get("modes") else f"{m1['orig_width']}x{m1['orig_height']}"
            mode2 = m2["modes"][0] if m2.get("modes") else f"{m2['orig_width']}x{m2['orig_height']}"

            # Primary monitor rotated according to saved default
            subprocess.run(["xrandr", "--output", m1["name"], "--auto", "--primary", "--mode", mode1, "--rotate", rot1], env=env, stderr=subprocess.DEVNULL)
            
            # Position second monitor next to monitor 1 based on monitor 1 rotated width
            rot_w1 = (m1["orig_height"] if m1.get("orig_height", 0) > 0 else 1080) if rot1 in ["left", "right"] else (m1["orig_width"] if m1.get("orig_width", 0) > 0 else 1920)
            subprocess.run(["xrandr", "--output", m2["name"], "--auto", "--mode", mode2, "--pos", f"{rot_w1}x0", "--rotate", rot2], env=env, stderr=subprocess.DEVNULL)
        elif len(monitors) == 1:
            m = monitors[0]
            subprocess.run(["xrandr", "--output", m["name"], "--auto", "--rotate", rot1], env=env, stderr=subprocess.DEVNULL)

    return start_display(url1=url1, url2=url2, monitor="both")

def apply_monitor_rotation(monitor_id="1", rotation="normal", save_default=False, restart_chromium=False, site=None):
    """
    Apply rotation to a specific monitor ('1' or '2') and optionally persist as default.
    """
    clean_id = str(monitor_id)
    clean_rot = rotation.lower()
    if clean_rot not in VALID_ROTATIONS:
        return False, f"Invalid rotation '{rotation}'. Must be one of {VALID_ROTATIONS}"

    if save_default:
        set_default_rotation(clean_id, clean_rot)

    env = get_x_env()
    if shutil.which("xrandr"):
        monitors = get_connected_monitors()
        if clean_id == "1":
            if len(monitors) >= 1:
                m1 = monitors[0]
                mode1 = m1["modes"][0] if m1.get("modes") else f"{m1['orig_width']}x{m1['orig_height']}"
                subprocess.run(["xrandr", "--output", m1["name"], "--auto", "--primary", "--mode", mode1, "--rotate", clean_rot], env=env, stderr=subprocess.DEVNULL)
                
                # If monitor 2 is present, adjust pos_x for monitor 2 so it stays side-by-side
                if len(monitors) >= 2:
                    m2 = monitors[1]
                    rot2 = m2.get("rotation", "normal")
                    mode2 = m2["modes"][0] if m2.get("modes") else f"{m2['orig_width']}x{m2['orig_height']}"
                    rot_w1 = (m1["orig_height"] if m1.get("orig_height", 0) > 0 else 1080) if clean_rot in ["left", "right"] else (m1["orig_width"] if m1.get("orig_width", 0) > 0 else 1920)
                    subprocess.run(["xrandr", "--output", m2["name"], "--auto", "--mode", mode2, "--pos", f"{rot_w1}x0", "--rotate", rot2], env=env, stderr=subprocess.DEVNULL)
        elif clean_id == "2":
            if len(monitors) < 2:
                # If save_default was requested, it's already saved
                return True, f"Monitor 2 rotation default saved to '{clean_rot}' (Monitor 2 is not currently connected)"
            m1 = monitors[0]
            m2 = monitors[1]
            rot1 = m1.get("rotation", "normal")
            mode2 = m2["modes"][0] if m2.get("modes") else f"{m2['orig_width']}x{m2['orig_height']}"
            rot_w1 = (m1["orig_height"] if m1.get("orig_height", 0) > 0 else 1080) if rot1 in ["left", "right"] else (m1["orig_width"] if m1.get("orig_width", 0) > 0 else 1920)
            subprocess.run(["xrandr", "--output", m2["name"], "--auto", "--mode", mode2, "--pos", f"{rot_w1}x0", "--rotate", clean_rot], env=env, stderr=subprocess.DEVNULL)

    if restart_chromium:
        time.sleep(0.5)
        kill_chromium(clean_id)
        time.sleep(0.5)
        if clean_id == "1":
            start_display(url1=site or "", monitor="1")
        elif clean_id == "2":
            start_display(url2=site or DEFAULT_AUTODARTS_URL2, monitor="2")

    msg = f"Monitor {clean_id} rotation set to {clean_rot}"
    if save_default:
        msg += " (saved as default)"
    return True, msg

def apply_display_rotations(rotations=None, save_default=False, restart_chromium=False):
    """
    Apply rotations for both monitors simultaneously and optionally save as defaults.
    rotations format: {"1": "left", "2": "right"}
    """
    rotations = rotations or {}
    rot1 = rotations.get("1", get_monitor_rotation("1", "left")).lower()
    rot2 = rotations.get("2", get_monitor_rotation("2", "right")).lower()

    if rot1 not in VALID_ROTATIONS:
        return False, f"Invalid rotation '{rot1}' for Monitor 1. Must be one of {VALID_ROTATIONS}"
    if rot2 not in VALID_ROTATIONS:
        return False, f"Invalid rotation '{rot2}' for Monitor 2. Must be one of {VALID_ROTATIONS}"

    if save_default:
        set_default_rotation("1", rot1)
        set_default_rotation("2", rot2)

    env = get_x_env()
    if shutil.which("xrandr"):
        monitors = get_connected_monitors()
        if len(monitors) >= 2:
            m1 = monitors[0]
            m2 = monitors[1]
            mode1 = m1["modes"][0] if m1.get("modes") else f"{m1['orig_width']}x{m1['orig_height']}"
            mode2 = m2["modes"][0] if m2.get("modes") else f"{m2['orig_width']}x{m2['orig_height']}"

            subprocess.run(["xrandr", "--output", m1["name"], "--auto", "--primary", "--mode", mode1, "--rotate", rot1], env=env, stderr=subprocess.DEVNULL)
            rot_w1 = (m1["orig_height"] if m1.get("orig_height", 0) > 0 else 1080) if rot1 in ["left", "right"] else (m1["orig_width"] if m1.get("orig_width", 0) > 0 else 1920)
            subprocess.run(["xrandr", "--output", m2["name"], "--auto", "--mode", mode2, "--pos", f"{rot_w1}x0", "--rotate", rot2], env=env, stderr=subprocess.DEVNULL)
        elif len(monitors) == 1:
            m = monitors[0]
            subprocess.run(["xrandr", "--output", m["name"], "--auto", "--rotate", rot1], env=env, stderr=subprocess.DEVNULL)

    if restart_chromium:
        time.sleep(0.5)
        start_display(monitor="both")

    msg = f"Display rotations updated (Mon 1: {rot1}, Mon 2: {rot2})"
    if save_default:
        msg += " and saved as defaults"
    return True, msg

def reset_display_to_defaults(restart_chromium=False):
    """Restore active displays to saved default orientations"""
    rot1 = get_monitor_rotation("1", "left")
    rot2 = get_monitor_rotation("2", "right")
    return apply_display_rotations({"1": rot1, "2": rot2}, save_default=False, restart_chromium=restart_chromium)

def toggle_monitor2(restart_chromium=False, site=None):
    """Toggle monitor 2 between vertical (left/right) and horizontal (normal) orientation"""
    monitors = get_connected_monitors()
    if len(monitors) < 2:
        return False, "Need at least 2 connected monitors"

    m2 = monitors[1]
    new_rotation = "normal" if m2.get("rotation") in ["left", "right"] else "left"
    return apply_monitor_rotation("2", new_rotation, save_default=False, restart_chromium=restart_chromium, site=site)
