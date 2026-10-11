FROM python:3.11-slim-bookworm

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required system tools for X11 control, Chromium kiosk, and process management
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-common \
    x11-xserver-utils \
    xdotool \
    procps \
    curl \
    && (apt-get install -y --no-install-recommends libraspberrypi-bin || true) \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set default runtime environment variables
ENV DATA_DIR=/data
ENV PORT=5000
ENV DISPLAY=:0
ENV PYTHONUNBUFFERED=1

# Ensure data directory and uploads folder structure exist
RUN mkdir -p /data/uploads/images

EXPOSE 5000

CMD ["python3", "app.py"]
