# Pi Display Control Interface

A web-based control panel for managing display scripts on your Raspberry Pi. This interface allows you to easily switch between different websites displayed on your Pi's screen and manage your list of saved websites.

## Features

- 🐳 **Docker Ready**: Fully containerized for easy deployment
- 🏠 **CasaOS Compatible**: Perfect for CasaOS deployment
- 🖥️ **Display Control**: Start and stop display scripts with different websites
- 📝 **Website Management**: Add, view, and delete saved websites
- 🎯 **Quick Access**: One-click display switching for saved websites
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile devices
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations

## Quick Start with Docker

### Option 1: Docker Compose (Recommended)

1. **Clone or download this repository:**
   ```bash
   cd "Pi interface"
   ```

2. **Start the container:**
   ```bash
   docker-compose up -d
   ```

3. **Access the control panel:**
   - From your Pi: `http://localhost:5000`
   - From another device: `http://<pi-ip-address>:5000`

### Option 2: Docker Run

```bash
docker run -d \
  --name pi-display-control \
  --restart unless-stopped \
  -p 5000:5000 \
  -v ~/:/host/home:ro \
  -v $(pwd)/data:/data \
  -e SCRIPT_PATH=/host/home/start.sh \
  -e WORK_DIR=/host/home \
  -e CONFIG_FILE=/data/websites.json \
  --privileged \
  spearg/pi-display-control:latest
```

## CasaOS Deployment

CasaOS makes deployment super easy:

### Method 1: Using Docker Compose in CasaOS

1. **In CasaOS, go to "App Store" or use the Docker Compose feature**
2. **Create a new compose file or use the provided `docker-compose.yml`**
3. **Adjust the volume mounts and environment variables as needed**
4. **Deploy!**

### Method 2: Using CasaOS App Store (Manual)

1. **In CasaOS, navigate to "App Store"**
2. **Click "Add App" → "Docker Image"**
3. **Use the following settings:**

   - **Image**: `gavinspear/pi-display-control:latest`
   - **Container Name**: `pi-display-control`
   - **Port**: `5000:5000`
   - **Volume Mounts**:
     - `/home/pi:/host/home:ro` (to access your start.sh script)
     - `/path/to/pi-display-control/data:/data` (for persistent storage)
   - **Environment Variables**:
     - `SCRIPT_PATH=/host/home/start.sh`
     - `WORK_DIR=/host/home`
     - `CONFIG_FILE=/data/websites.json`
   - **Privileged Mode**: Enable (needed for pkill command)

4. **Deploy and access at**: `http://<casaos-ip>:5000`

### Method 3: CasaOS docker-compose.yml Format

Create a `docker-compose.yml` in CasaOS:

```yaml
version: '3.8'

services:
  pi-display-control:
    image: gavinspear/pi-display-control:latest
    container_name: pi-display-control
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ~/:/host/home:ro
      - ./data:/data
    environment:
      - SCRIPT_PATH=/host/home/start.sh
      - WORK_DIR=/host/home
      - CONFIG_FILE=/data/websites.json
    privileged: true
```

## Docker Hub

The image is available on Docker Hub:
```bash
docker pull gavinspear/pi-display-control:latest
```

**Tags available:**
- `latest` - Latest stable release
- `v1.0.0` - Specific version tags (as released)
- `main-<sha>` - Development builds from main branch

## Building from Source

If you want to build the Docker image yourself:

```bash
# Build for your architecture
docker build -t pi-display-control .

# Build multi-arch (amd64, arm64, arm/v7) for Raspberry Pi
docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t gavinspear/pi-display-control:latest .
```

## Local Python Installation (Alternative)

If you prefer not to use Docker:

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
   - From another device: `http://<pi-ip-address>:5000`

## Usage

### Using the Control Panel

1. **Start a Display**: Click "Start Display" next to any saved website
2. **Stop Display**: Click the "Stop Display" button at the top
3. **Add Website**: Fill in the form at the bottom to add a new website
4. **Delete Website**: Click "Delete" next to any website to remove it

### Default Websites

The system comes with two default websites:
- **Autodarts Board** (default - no URL needed)
- **8-bit Website** (https://8bit.website.com)

These can be modified or deleted through the interface.

## Configuration

### Environment Variables

The following environment variables can be set:

- `SCRIPT_PATH` - Path to your start.sh script (default: `/host/home/start.sh` in Docker, `~/start.sh` locally)
- `WORK_DIR` - Working directory for scripts (default: `/host/home` in Docker, `~` locally)
- `CONFIG_FILE` - Location of websites.json (default: `/data/websites.json` in Docker, `websites.json` locally)
- `PORT` - Server port (default: `5000`)
- `FLASK_ENV` - Set to `production` for production mode (default: `production`)

### Volume Mounts

**Required:**
- Mount your home directory (or script location) as read-only: `-v ~/:/host/home:ro`
- Mount a data directory for persistent storage: `-v ./data:/data`

**Optional:**
- If your scripts are elsewhere, mount that directory instead

### Script Location

Make sure your `start.sh` script exists and is executable:
```bash
chmod +x ~/start.sh
```

The Docker container will access it via the mounted volume at `/host/home/start.sh`.

## File Structure

```
Pi interface/
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker Compose configuration
├── .dockerignore        # Docker ignore file
├── app.py              # Flask backend server
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html     # Main control page
├── static/
│   ├── style.css      # Styling
│   └── script.js      # Frontend JavaScript
└── data/              # Persistent data (created on first run)
    └── websites.json  # Saved websites
```

## API Endpoints

- `GET /api/websites` - Get list of saved websites
- `POST /api/websites` - Add a new website
- `DELETE /api/websites/<index>` - Delete a website by index
- `POST /api/display` - Start display with a URL
- `DELETE /api/display` - Stop the current display

## Troubleshooting

### Script not found error
- Make sure `start.sh` exists in your home directory
- Check that the script has execute permissions: `chmod +x ~/start.sh`
- Verify the volume mount is correct in your Docker configuration
- Check that `SCRIPT_PATH` environment variable matches the mounted path

### Port already in use
- Change the port mapping in docker-compose.yml: `"8080:5000"` (external:internal)
- Or set `PORT` environment variable to a different value

### Can't access from another device
- Make sure the server is bound to `0.0.0.0` (already configured)
- Check your Pi's firewall settings
- Verify both devices are on the same network
- In CasaOS, check if the port is exposed correctly

### Container keeps restarting
- Check logs: `docker logs pi-display-control`
- Verify all volume mounts are accessible
- Ensure the script path exists in the mounted volume

### Permission denied errors
- The container needs `privileged: true` to use `pkill` command
- Alternatively, you can run with specific capabilities

## Publishing to Docker Hub

To publish a new version:

1. **Build and tag:**
   ```bash
   docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 \
     -t gavinspear/pi-display-control:latest \
     -t gavinspear/pi-display-control:v1.0.0 \
     --push .
   ```

2. **Or use GitHub Actions** (automated on push to main branch)

## License

Free to use and modify for your projects.
