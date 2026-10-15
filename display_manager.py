#!/usr/bin/env python3
"""
Pi Display Manager
Pure Python replacement for legacy display shell scripts.
Manages multi-monitor setup, screen power states, Chromium kiosk instances, window positioning,
and customizable persistent monitor rotations.
"""

from display import (
    get_x_env,
    find_chromium,
    fix_chromium_preferences,
    kill_chromium,
    get_connected_monitors,
    get_xdotool_windows,
    position_window,
    start_display,
    blank_screen,
    wake_screen,
    toggle_monitor2,
    apply_monitor_rotation,
    apply_display_rotations,
    reset_display_to_defaults,
    load_display_config,
    get_monitor_rotation,
    set_default_rotation,
    VALID_ROTATIONS,
    DEFAULT_AUTODARTS_URL,
    DEFAULT_AUTODARTS_URL2
)

# ----------------------------------------------------------------------
# Command-Line Interface (CLI) Entrypoint
# ----------------------------------------------------------------------
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Pi Display Control CLI")
    subparsers = parser.add_subparsers(dest="action", help="Action to execute")

    # start command
    start_parser = subparsers.add_parser("start", help="Start or update display")
    start_parser.add_argument("url1", nargs="?", default="", help="URL for Monitor 1")
    start_parser.add_argument("url2", nargs="?", default="", help="URL for Monitor 2")
    start_parser.add_argument("--monitor", choices=["1", "2", "both"], default="both", help="Target monitor")

    # blank command
    subparsers.add_parser("blank", help="Blank/power off display screens")

    # wake command
    wake_parser = subparsers.add_parser("wake", help="Wake/power on display screens and apply default rotations")
    wake_parser.add_argument("url1", nargs="?", default="", help="URL for Monitor 1")
    wake_parser.add_argument("url2", nargs="?", default="", help="URL for Monitor 2")

    # rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate monitor and optionally set as startup default")
    rotate_parser.add_argument("--monitor", choices=["1", "2", "both"], default="1", help="Target monitor")
    rotate_parser.add_argument("--rotation", choices=VALID_ROTATIONS, required=True, help="Orientation")
    rotate_parser.add_argument("--save-default", action="store_true", help="Save this rotation as default for restarts")
    rotate_parser.add_argument("--restart", action="store_true", help="Restart Chromium to adjust to new resolution")

    # set-default-rotation command
    def_parser = subparsers.add_parser("set-default-rotation", help="Configure persistent default startup rotation for a monitor")
    def_parser.add_argument("--monitor", choices=["1", "2"], required=True, help="Target monitor (1 or 2)")
    def_parser.add_argument("--rotation", choices=VALID_ROTATIONS, required=True, help="Default orientation")

    # apply-defaults command
    apply_def_parser = subparsers.add_parser("apply-defaults", help="Re-apply saved default rotations to screens")
    apply_def_parser.add_argument("--restart", action="store_true", help="Restart Chromium")

    # toggle command
    toggle_parser = subparsers.add_parser("toggle-monitor2", help="Toggle monitor 2 vertical/horizontal orientation")
    toggle_parser.add_argument("--restart", action="store_true", help="Restart Chromium on monitor 2")
    toggle_parser.add_argument("--url", default="", help="URL for monitor 2 if restarting")

    # status command
    subparsers.add_parser("status", help="Show connected monitor status and rotation defaults")

    args = parser.parse_args()

    if args.action == "start":
        success, msg = start_display(url1=args.url1, url2=args.url2, monitor=args.monitor)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "blank":
        success, msg = blank_screen()
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "wake":
        success, msg = wake_screen(url1=args.url1, url2=args.url2)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "rotate":
        if args.monitor == "both":
            success, msg = apply_display_rotations({"1": args.rotation, "2": args.rotation}, save_default=args.save_default, restart_chromium=args.restart)
        else:
            success, msg = apply_monitor_rotation(args.monitor, args.rotation, save_default=args.save_default, restart_chromium=args.restart)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "set-default-rotation":
        try:
            set_default_rotation(args.monitor, args.rotation)
            print(f"[OK] Monitor {args.monitor} default rotation saved as '{args.rotation}'")
        except Exception as e:
            print(f"[ERROR] Failed to save default: {e}")
    elif args.action == "apply-defaults":
        success, msg = reset_display_to_defaults(restart_chromium=args.restart)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "toggle-monitor2":
        success, msg = toggle_monitor2(restart_chromium=args.restart, site=args.url)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "status":
        monitors = get_connected_monitors()
        def1 = get_monitor_rotation("1", "left")
        def2 = get_monitor_rotation("2", "right")
        print(f"Found {len(monitors)} connected monitors:")
        for idx, m in enumerate(monitors, 1):
            default_rot = def1 if idx == 1 else (def2 if idx == 2 else "normal")
            print(f"  Monitor {idx} ({m['name']}): {m['width']}x{m['height']} (current rotation: {m['rotation']}, saved default: {default_rot}, pos: +{m['pos_x']}+{m['pos_y']})")
        print(f"Configured Startup Defaults: Monitor 1 = {def1}, Monitor 2 = {def2}")
    else:
        parser.print_help()
