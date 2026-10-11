#!/bin/sh

# xinitrc for Raspberry Pi
# Sets up the X11 environment for the Docker container to connect to.
# The Docker container handles launching Chromium via the mounted X11 socket.

# Disable screen blanking / DPMS so monitors stay on
xset s off
xset s noblank
xset -dpms

# Allow local and Docker container connections to the X server
xhost +local:root
xhost +local:docker

# Keep the X session alive indefinitely — Docker container does the rest
exec tail -f /dev/null
