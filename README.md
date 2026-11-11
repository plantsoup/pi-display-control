# pi-display-control

A Flask web UI, REST API, and CLI tool for managing single- or dual-monitor Chromium kiosk displays on a Raspberry Pi.

Originally built to run an Autodarts board on one vertical monitor and a photo slideshow or status dashboard on a second monitor—without having to SSH in to run `xrandr` commands or kill hung Chromium processes by hand.

## What it does

- **Independent dual-monitor control**: Drive Monitor 1, Monitor 2, or both from the web UI or CLI. Each screen runs its own isolated Chromium profile (`~/.config/chromium-autodarts-monitor1` and `monitor2`) and is positioned onto the right X11 output using `xrandr` and `xdotool`.
- **Clean Chromium kiosk launches**: Automatically patches Chromium's `Preferences` file before launch (`exit_type: Normal`, `exited_cleanly: true`) so power cycles never leave the "Chromium didn't shut down correctly" bubble on screen.
- **Per-monitor rotation & geometry**: Rotate either monitor (`normal`, `left`, `right`, `inverted`) on the fly. When Monitor 1 is rotated between portrait and landscape, Monitor 2's X offset (`--pos`) is recalculated automatically so the two displays stay side-by-side without overlapping.
- **Persistent wake & startup defaults**: Save a default rotation and default content (`website`, `image`, or `slideshow`) for each monitor in `data/display_settings.json`. Waking the screens—whether from the web UI, a schedule, or `.xinitrc` on boot—restores those rotations and opens each monitor's default view.
- **Hardware monitor detection**: Queries `xrandr` for active outputs and falls back to Linux DRM sysfs (`/sys/class/drm/card*-*/status`) if X11 isn't reachable yet. Virtual/dummy connectors (`NOOP`, `VIRTUAL`, `DUMMY`, `WRITEBACK`) and unplugged ports are filtered out, and the UI adapts to 0, 1, or 2 connected screens.
- **Built-in image viewer & slideshow (`/viewer`)**: Upload images (`png`, `jpg`, `jpeg`, `gif`, `bmp`, `webp`, `svg`) and display either a static wallpaper or a cycling slideshow. Supports shuffle or sequential order, custom intervals, `cover` / `contain` scaling, and `fade` / `slide` / `instant` transitions.
- **Screen power control**: Blank and wake displays using `vcgencmd display_power` alongside `xrandr --off` / `--auto`. Supports blanking all monitors or blanking an individual monitor (`--monitor 1` or `--monitor 2`).
- **Time-of-day scheduler**: Background thread that triggers `wake`, `blank`, `website`, or `slideshow` actions at set times (`HH:MM`) on selected days of the week. Schedules can target the local Pi, a specific remote Pi, or all connected Pis.
- **Multi-Pi support**: Link additional Raspberry Pis running `pi-display-control` over LAN IPs, `.local` hostnames, or HTTPS URLs.
  - Switch the active target Pi in the header to control a remote Pi's monitors, rotations, websites, images, and schedules through a server-to-server proxy (avoiding browser CORS and mixed-content issues).
  - Broadcast a layout, wake, or blank command to every Pi at once.
  - Stream the main Pi's slideshow/images directly to a secondary Pi's browser, or sync saved websites, slideshow settings, and uploaded image files across nodes.

## Setup

### Requirements

- Python 3
- X11 tools on the Pi: `xrandr`, `xdotool`, `chromium` (or `chromium-browser`), and optionally `unclutter` and `openbox` / `fluxbox` for kiosk sessions.

Install the Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

*(Note: `app.py` automatically checks for `.venv`, `venv`, or `env` in the project directory, so you can also invoke `python3 app.py` directly once the virtualenv is created.)*

### Running the web server

```bash
python3 app.py
```

By default the server listens on `http://0.0.0.0:5000`:

- Control panel: `http://<pi-ip>:5000`
- Fullscreen slideshow/image viewer: `http://<pi-ip>:5000/viewer`

### Booting into kiosk mode (`.xinitrc`)

An example [`.xinitrc`](.xinitrc) is included for starting X11 directly into your saved display configuration:

1. Hides the idle mouse cursor with `unclutter`.
2. Starts `openbox` or `fluxbox` if installed.
3. Calls `python3 display_manager.py wake`, which powers on the HDMI outputs, applies your saved monitor rotations, and launches Chromium on each screen with its configured default content.

## CLI usage (`display_manager.py`)

You can control the displays directly from the terminal or scripts without going through the web UI:

```bash
# Check connected monitors, active resolutions, and saved startup defaults
python3 display_manager.py status

# Start displays (uses saved defaults if URLs are omitted)
python3 display_manager.py start "https://play.autodarts.io" "https://example.com"
python3 display_manager.py start "https://play.autodarts.io" --monitor 1

# Blank (power off) or wake (power on + restore defaults) - both monitors or single monitor
python3 display_manager.py blank                    # blanks both screens
python3 display_manager.py blank --monitor 1        # blanks Monitor 1 only
python3 display_manager.py blank --monitor 2        # blanks Monitor 2 only
python3 display_manager.py wake --monitor 1         # wakes Monitor 1 only
python3 display_manager.py wake                     # wakes all screens

# Rotate a monitor immediately (normal, left, right, inverted)
python3 display_manager.py rotate --monitor 1 --rotation left --save-default --restart
python3 display_manager.py rotate --monitor 2 --rotation right --save-default --restart

# Save default startup rotation without changing the current screen
python3 display_manager.py set-default-rotation --monitor 1 --rotation left
python3 display_manager.py set-default-rotation --monitor 2 --rotation right

# Save default startup/wake content per monitor
python3 display_manager.py set-default-content --monitor 1 --type website --url "https://play.autodarts.io" --name "Autodarts Board"
python3 display_manager.py set-default-content --monitor 2 --type slideshow --mode random --interval 30 --fit cover
python3 display_manager.py set-default-content --monitor 2 --type image --image "wallpaper.jpg" --fit cover

# Re-apply saved default rotations
python3 display_manager.py apply-defaults --restart

# Quick toggle Monitor 2 between vertical and horizontal
python3 display_manager.py toggle-monitor2 --restart
```

## Environment variables

All runtime data (website list, uploaded images, slideshow settings, schedules, monitor defaults, and linked Pi nodes) is stored as JSON in `DATA_DIR`. If `/data` exists and is writable (e.g. in a container), it is used automatically; otherwise `./data` inside the repo is used.

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `5000` | Port for the Flask server and local `/viewer` URLs |
| `DATA_DIR` | `/data` or `./data` | Directory for JSON config files and uploaded images |
| `UPLOAD_FOLDER` | `$DATA_DIR/uploads/images` | Directory where uploaded images are stored |
| `WORK_DIR` | `~` | Home directory used for locating user configs |
| `DEFAULT_DISPLAY_URL` | `https://play.autodarts.io` | Fallback URL for Monitor 1 when no URL is configured |
| `DEFAULT_DISPLAY_URL2` | `DEFAULT_DISPLAY_URL` | Fallback URL for Monitor 2 when no URL is configured |
| `MAIN_PI_URL` | *(auto-detected)* | Optional base URL override for the main Pi (used when streaming to remote Pis) |
| `SECONDARY_PI_URL` | *(none)* | Optional URL to pre-populate a secondary Pi node on first run |
| `PI_NODE_ROLE` | *(auto-detected)* | Set to `main` or `secondary` to override hostname-based node role detection |

## API overview

### Display & hardware
- `GET /api/status` — Current display state, active mode, item counts, and server time.
- `GET /api/display/monitors` — Connected monitors, resolutions, active rotations, and saved startup defaults.
- `POST /api/display` — Launch a website, single image, slideshow, or per-monitor mix (`monitor`: `1`, `2`, or `both`; optional `save_default: true`).
- `DELETE /api/display` — Blank screens and stop Chromium (supports `?monitor=1`, `?monitor=2`, or `?monitor=both`).
- `POST /api/display/blank` — Blank screens and stop Chromium (`{"monitor": "1" | "2" | "both"}`).
- `POST /api/display/wake` — Wake screens, restore default rotations, and launch default content (supports `{"monitor": "1" | "2" | "both"}`).
- `POST /api/display/rotate` — Rotate `1`, `2`, or `both` (`normal`, `left`, `right`, `inverted`), with optional `save_default` and `restart_browser`.
- `POST /api/display/default-content` — Save default wake/startup content for Monitor 1, 2, or both (optional `apply_now: true`).
- `POST /api/display/defaults` — Bulk-save default rotations and/or default content.
- `POST /api/display/reset-defaults` — Re-apply saved default rotations to connected monitors.

### Media & websites
- `GET /api/websites` / `POST /api/websites` / `DELETE /api/websites/<index>` — Manage saved URLs.
- `GET /api/images` / `POST /api/images` / `DELETE /api/images/<index>` — List, upload (`multipart/form-data`), or delete images.
- `GET /api/images/<filename>` — Serve an uploaded image file.
- `GET /api/slideshow` / `POST /api/slideshow` — Read or update slideshow settings (`mode`, `interval`, `transition`, `fit`, `selected_images`, `background_color`).
- `GET /api/viewer/data` — JSON feed used by the `/viewer` page.

### Schedules
- `GET /api/schedules` / `POST /api/schedules` — List or create time-of-day schedules (`time` in `HH:MM`, `days`, `action`, and `params.target_node` set to `local`, `all`, or a node ID).
- `PUT /api/schedules/<id>/toggle` — Enable or disable a schedule.
- `DELETE /api/schedules/<id>` — Remove a schedule.

### Multi-Pi nodes
- `GET /api/nodes` — List local Pi metadata and configured remote Pi nodes.
- `GET /api/nodes/overview` — Poll live status and connected monitor counts across all Pis concurrently.
- `POST /api/nodes/probe` — Test connectivity to another Pi and inspect its monitors before saving.
- `POST /api/nodes` / `PUT /api/nodes/<id>` / `DELETE /api/nodes/<id>` — Add, update, or remove a remote Pi node.
- `GET /api/nodes/<id>/status` — Poll live status for a single node.
- `POST /api/nodes/<id>/display` — Send a `display`, `wake`, `blank`, or `rotate` action to a specific Pi (supports `stream_from_main: true`).
- `POST /api/nodes/broadcast` — Broadcast an action across all enabled Pis.
- `POST /api/nodes/<id>/sync` — Push saved websites, slideshow settings, and/or uploaded images to a remote Pi.
- `ANY /api/nodes/<id>/proxy/<api_path>` — Server-to-server proxy to a remote Pi's `/api/*` endpoints (with `X-Pi-Proxy-Hop` loop prevention).

## Tests

```bash
python3 test_app.py
```
