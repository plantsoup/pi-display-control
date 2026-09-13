# Pi Display Control & Image Slideshow Studio

A comprehensive, modern web control panel and display engine for Raspberry Pi multi-monitor setups. It allows switching displays between Autodarts boards, custom websites, single image displays, and automated image slideshows with randomization, customizable time intervals, and time-of-day scheduled triggers.

## Key Features

- 🖥️ **Multi-Monitor Display Control**: Independent control for Monitor 1, Monitor 2, or Both Displays.
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
- `POST /api/display` - Start display with a Website, Image, or Slideshow on Monitor 1, 2, or Both.
- `DELETE /api/display` - Blank / turn off display screens.
- `POST /api/display/wake` - Wake / turn on display screens.

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
- `POST /api/schedules` - Create a new time-of-day schedule.
- `PUT /api/schedules/<id>/toggle` - Toggle schedule active/inactive.
- `DELETE /api/schedules/<id>` - Delete a schedule.

---

## Configuration & Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5000` | HTTP server listening port |
| `DATA_DIR` | `/data` or `./data` | Directory for JSON data and uploaded image storage |
| `SCRIPT_PATH` | `./start.sh` | Path to the monitor launcher script |
| `BLANK_SCREEN_PATH` | `./blank-screen.sh` | Path to the screen blanking script |
| `WAKE_SCREEN_PATH` | `./wake-screen.sh` | Path to the screen waking script |

---

## Testing

Run the automated test suite:
```bash
python3 test_app.py
```
