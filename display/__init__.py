"""
Pi Display Control hardware & display module.
Provides low-level and high-level interfaces for monitor detection, Chromium management, and screen power.
"""

from .browser import (
    get_x_env,
    find_chromium,
    fix_chromium_preferences,
    kill_chromium,
    _launch_chromium_process
)
from .monitors import get_connected_monitors
from .window import get_xdotool_windows, position_window
from .manager import start_display, DEFAULT_AUTODARTS_URL, DEFAULT_AUTODARTS_URL2
from .config import (
    load_display_config,
    save_display_config,
    get_monitor_rotation,
    set_default_rotation,
    get_monitor_default_content,
    set_monitor_default_content,
    resolve_monitor_default_url,
    normalize_default_content,
    VALID_ROTATIONS,
    ROTATION_METADATA,
    VALID_CONTENT_TYPES
)
from .power import (
    blank_screen,
    wake_screen,
    toggle_monitor2,
    _set_display_power,
    apply_monitor_rotation,
    apply_display_rotations,
    reset_display_to_defaults
)

__all__ = [
    'get_x_env',
    'find_chromium',
    'fix_chromium_preferences',
    'kill_chromium',
    'get_connected_monitors',
    'get_xdotool_windows',
    'position_window',
    'start_display',
    'blank_screen',
    'wake_screen',
    'toggle_monitor2',
    'apply_monitor_rotation',
    'apply_display_rotations',
    'reset_display_to_defaults',
    'load_display_config',
    'save_display_config',
    'get_monitor_rotation',
    'set_default_rotation',
    'get_monitor_default_content',
    'set_monitor_default_content',
    'resolve_monitor_default_url',
    'normalize_default_content',
    'VALID_ROTATIONS',
    'VALID_CONTENT_TYPES',
    'ROTATION_METADATA',
    'DEFAULT_AUTODARTS_URL',
    'DEFAULT_AUTODARTS_URL2'
]
