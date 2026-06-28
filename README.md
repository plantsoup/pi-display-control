# Pi Display Control Interface

A web-based control panel for managing display scripts on your Raspberry Pi. This interface allows you to easily switch between different websites displayed on your Pi's screen and manage your list of saved websites.


- 🖥️ **Display Control**: Start and stop display scripts with different websites
- 📝 **Website Management**: Add, view, and delete saved websites
- 🎯 **Quick Access**: One-click display switching for saved websites
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile devices
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations



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


### Permission denied errors
- The container needs `privileged: true` to use `pkill` command
- Alternatively, you can run with specific capabilities

