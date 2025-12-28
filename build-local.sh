#!/bin/bash
# Build script for local testing (single architecture)

set -e

IMAGE_NAME="pi-display-control"
VERSION="${1:-latest}"

echo "Building Docker image locally: ${IMAGE_NAME}:${VERSION}"

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
  x86_64) PLATFORM="linux/amd64" ;;
  aarch64|arm64) PLATFORM="linux/arm64" ;;
  armv7l) PLATFORM="linux/arm/v7" ;;
  *) PLATFORM="linux/amd64" ;;
esac

echo "Building for platform: ${PLATFORM}"

docker build \
  --platform ${PLATFORM} \
  -t "${IMAGE_NAME}:${VERSION}" \
  -t "${IMAGE_NAME}:latest" \
  .

echo "✅ Successfully built ${IMAGE_NAME}:${VERSION}"
echo ""
echo "To test locally:"
echo "  docker-compose up"

