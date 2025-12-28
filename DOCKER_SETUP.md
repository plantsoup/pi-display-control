# Docker Setup Guide

## Quick Start

### 1. Login to Docker Hub

Before pushing, you need to authenticate:

```bash
docker login
```

Enter your Docker Hub username and password (or access token).

### 2. Create Repository on Docker Hub

1. Go to https://hub.docker.com/repositories
2. Click "Create Repository"
3. Name it: `pi-display-control`
4. Set visibility (public or private)
5. Click "Create"

### 3. Build and Push

**Option A: Build locally first (recommended for testing)**
```bash
./build-local.sh
```

**Option B: Build and push to Docker Hub**
```bash
# Make sure you're logged in first
docker login

# Build and push
./build.sh v1.0.0 true
```

**Option C: Build multi-arch and push**
```bash
# First, ensure buildx is set up
docker buildx create --use --name multiarch

# Then build and push
./build.sh v1.0.0 true
```

## Build Scripts Explained

### `build-local.sh`
- Builds for your current architecture only
- Faster build times
- Good for local testing
- Doesn't push anywhere

### `build.sh`
- Builds for multiple architectures (amd64, arm64, arm/v7)
- Supports Raspberry Pi (ARM)
- Can push to Docker Hub
- Usage: `./build.sh <version> [push]`
  - `./build.sh v1.0.0` - Build locally, don't push
  - `./build.sh v1.0.0 true` - Build and push to Docker Hub

## Troubleshooting Push Errors

### Error: "push access denied"
- Make sure you're logged in: `docker login`
- Verify the repository exists on Docker Hub
- Check your Docker Hub username matches the image name prefix

### Error: "repository does not exist"
1. Create the repository on Docker Hub first
2. Make sure the name matches: `spearg/pi-display-control`

### Error: "insufficient_scope"
- Your Docker Hub account may need verification
- Try using an access token instead of password
- Generate token at: https://hub.docker.com/settings/security

## Testing Locally

After building locally:

```bash
# Build local image
./build-local.sh

# Update docker-compose.yml to use local image (see below)
# Then run
docker-compose up
```

To use local image in docker-compose.yml, change:
```yaml
image: spearg/pi-display-control:latest
```
to:
```yaml
image: pi-display-control:latest
build: .
```

Or use the local image directly:
```bash
docker run -d \
  --name pi-display-control \
  -p 5000:5000 \
  -v ~/:/host/home:ro \
  -v $(pwd)/data:/data \
  -e SCRIPT_PATH=/host/home/start.sh \
  --privileged \
  pi-display-control:latest
```

## For CasaOS

Once pushed to Docker Hub, you can pull directly in CasaOS:

1. Image name: `spearg/pi-display-control:latest`
2. Or use the docker-compose.yml provided

