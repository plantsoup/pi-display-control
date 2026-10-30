# Pi Display Control & Image Slideshow Studio

A comprehensive, modern web control panel and display engine for Raspberry Pi multi-monitor setups. It allows switching displays between Autodarts boards, custom websites, single image displays, and automated image slideshows with randomization, customizable time intervals, and time-of-day scheduled triggers.

## Key Features

- 🖥️ **Multi-Monitor Display Control**: Independent control for Monitor 1, Monitor 2, or Both Displays.
- 🎯 **Configurable Wake & Startup Defaults**:
  - Configure default site or wallpaper for Monitor 1 and Monitor 2 independently.
  - Automatically loads your chosen site, single image wallpaper, or randomized slideshow whenever monitors are woken up, restarted, or booted.
  - Easily manage defaults directly from the Monitor Mixer in the Web UI, REST API, or CLI.
- 🔗 **Multi-Pi Fleet & Remote Displays**:
  - Connect and manage multiple Raspberry Pis running Pi Display Control across LAN IPs, `.local` mDNS hostnames, or custom HTTPS domains via the Web UI, REST API, or environment variables.
  - **1-Click Target Pi Switcher** in the header to control any connected Pi's monitors, orientations, websites, images, slideshows, power state, and schedules via server-side proxy (no CORS issues).
  - **Connected Pis & Display Wall** tab to view all Pis and their displays together, rotate remote monitors, broadcast content/power (`Wake All` / `Blank All`) across all Pis, stream Main Pi's slideshow/images directly to Secondary Pi's Chromium kiosk, or sync websites and images between Pis.
- 🖼️ **Image Slideshow Studio**:
  - **Randomize Mode (Shuffle)** or Sequential cycling.
  - **Timing Intervals**: Change images automatically (5s, 10s, 30s, 1m, 5m, custom interval).
  - **Fit Modes**: Contain (preserve aspect ratio) or Cover (fill full display).
  - **Hardware-Accelerated Transitions**: Smooth crossfade, slide-in, or instant cut.
  - **Dedicated Fullscreen Kiosk Viewer** (`/viewer` / `/slideshow`).
- ⏰ **Automated Time Scheduler**:
  - Automatically switch displays or start randomized slideshows at specific times of day (e.g. 08:00 Wake & Random Slideshow, 19:00 Switch to Autodarts, 23:00 Blank Screen).
  - Enable/disable schedule toggles with minute-precision background runner.
- 🌐 **Website & Autodarts Management**: Save, launch, and manage custom URLs or default Autodarts boards.
- 🌙 **Screen Power Management**: Instant Wake Screen and Blank Screen commands.
- 🎨 **Modern Dark UI**: Glassmorphic styling, responsive layout, live status tracking, and toast alerts.

---

## Quick Start

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python3 app.py
   ```

3. **Access the control panel:**
   - From your Pi: `http://localhost:5000`
   - From another device on your network: `http://<pi-ip-address>:5000`
   - Fullscreen Kiosk Viewer directly: `http://<pi-ip-address>:5000/viewer`

---

## API Endpoints

### Display & Status
- `GET /api/status` - Live display status, running mode, counts, and server time.
- `GET /api/display/monitors` - Discovered monitors, active orientations, and saved default rotations and default content.
- `POST /api/display` - Start display with a Website, Image, or Slideshow on Monitor 1, 2, or Both (optional `save_default: true`).
- `DELETE /api/display` - Blank / turn off display screens.
- `POST /api/display/wake` - Wake / turn on display screens and launch configured default site/wallpaper.
- `POST /api/display/default-content` - Save persistent default site or wallpaper for Monitor 1, 2, or Both.
- `POST /api/display/defaults` - Bulk save persistent default orientations and/or default sites/wallpapers.
- `POST /api/display/reset-defaults` - Restore active displays to saved default orientations and default content.

### Image Library & Slideshow
- `GET /api/images` - List uploaded images.
- `POST /api/images` - Upload new image (PNG, JPG, JPEG, GIF, WEBP, SVG).
- `DELETE /api/images/<index>` - Delete an uploaded image.
- `GET /api/slideshow` - Get slideshow configuration.
- `POST /api/slideshow` - Update slideshow mode (`random`/`sequential`), interval, transitions, and fit.
- `GET /api/viewer/data` - Kiosk viewer data sync endpoint.

### Websites
- `GET /api/websites` - List saved websites.
- `POST /api/websites` - Add a new website URL.
- `DELETE /api/websites/<index>` - Delete a website by index.

### Automated Scheduler
- `GET /api/schedules` - List all scheduled time triggers.
- `POST /api/schedules` - Create a new time-of-day schedule (supports targeting `local`, `all`, or a specific connected Pi).
- `PUT /api/schedules/<id>/toggle` - Toggle schedule active/inactive.
- `DELETE /api/schedules/<id>` - Delete a schedule.

### Connected Pis & Multi-Display Fleet
- `GET /api/nodes` - List local and connected remote Pi nodes.
- `GET /api/nodes/overview` - Concurrent live health, display status, and discovered monitors across all Pis.
- `POST /api/nodes/probe` - Test connectivity and auto-discover a Pi running Pi Display Control.
- `POST /api/nodes` - Connect a new remote Pi node.
- `PUT /api/nodes/<id>` - Update local or remote Pi node configuration.
- `DELETE /api/nodes/<id>` - Disconnect a remote Pi node.
- `POST /api/nodes/<id>/display` - Dispatch display content, stream Main Pi viewer, wake, blank, or rotate on a target Pi.
- `POST /api/nodes/broadcast` - Broadcast display content, wake, or blank across all connected Pis.
- `POST /api/nodes/<id>/sync` - Sync saved websites, slideshow settings, and uploaded images to a remote Pi.
- `ANY /api/nodes/<id>/proxy/<api_path>` - Transparent server-to-server API & media proxy to a connected Pi.

---

## Configuration & Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5000` | HTTP server listening port |
| `DATA_DIR` | `/data` or `./data` | Directory for JSON data and uploaded image storage |
| `WORK_DIR` | `~` | Home/working directory for user configs |
| `MAIN_PI_URL` | *(auto-detected)* | Optional public base URL override for Main Pi |
| `SECONDARY_PI_URL` | *(none)* | Optional URL to pre-seed a connected Secondary Pi on first run |
| `PI_NODE_ROLE` | *(auto-detected)* | Optional `'main'` or `'secondary'` override for default node seeding |
| `DEFAULT_DISPLAY_URL` | `https://play.autodarts.io` | Default fallback kiosk URL for Monitor 1 |
| `DEFAULT_DISPLAY_URL2` | `DEFAULT_DISPLAY_URL` | Default fallback kiosk URL for Monitor 2 |

---

## Standalone CLI Display Control

All display controls can also be triggered directly from Python CLI without running the web server:

```bash
# Start or update display
python3 display_manager.py start "https://play.autodarts.io" "https://example.com"

# Blank/power off screens
python3 display_manager.py blank

# Wake/power on screens (loads saved default site/wallpaper)
python3 display_manager.py wake

# Configure default site or wallpaper for monitors when woken/started
python3 display_manager.py set-default-content --monitor 1 --type website --url "https://play.autodarts.io" --name "Autodarts Board"
python3 display_manager.py set-default-content --monitor 2 --type slideshow --mode random --interval 30
python3 display_manager.py set-default-content --monitor 2 --type image --image "flower.jpg" --fit cover

# Configure default monitor orientation
python3 display_manager.py set-default-rotation --monitor 1 --rotation left
python3 display_manager.py set-default-rotation --monitor 2 --rotation right

# Restore displays to saved default orientations and default content
python3 display_manager.py apply-defaults --restart

# Toggle monitor 2 vertical/horizontal rotation
python3 display_manager.py toggle-monitor2 --restart

# Check connected monitors
python3 display_manager.py status
```

---

## Testing

Run the automated test suite:
```bash
python3 test_app.py
```
