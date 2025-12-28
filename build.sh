#!/bin/bash
# Build script for Pi Display Control Docker image

set -e

IMAGE_NAME="spearg/pi-display-control"
VERSION="${1:-latest}"
PUSH="${2:-false}"

echo "Building Docker image: ${IMAGE_NAME}:${VERSION}"
echo "Push to registry: ${PUSH}"

# Build for multiple architectures (supports Raspberry Pi)
if [ "$PUSH" = "true" ]; then
    echo "⚠️  Make sure you're logged into Docker Hub: docker login"
    docker buildx build \
      --platform linux/amd64,linux/arm64,linux/arm/v7 \
      -t "${IMAGE_NAME}:${VERSION}" \
      -t "${IMAGE_NAME}:latest" \
      --push .
    echo "✅ Successfully built and pushed ${IMAGE_NAME}:${VERSION}"
else
    echo "🔨 Building for local architecture only (use build-local.sh for faster local builds)..."
    # Detect local architecture
    ARCH=$(uname -m)
    case $ARCH in
      x86_64) PLATFORM="linux/amd64" ;;
      aarch64|arm64) PLATFORM="linux/arm64" ;;
      armv7l) PLATFORM="linux/arm/v7" ;;
      *) PLATFORM="linux/amd64" ;;
    esac
    echo "Building for platform: ${PLATFORM}"
    docker buildx build \
      --platform ${PLATFORM} \
      -t "${IMAGE_NAME}:${VERSION}" \
      -t "${IMAGE_NAME}:latest" \
      --load .
    echo "✅ Successfully built ${IMAGE_NAME}:${VERSION} locally"
    echo ""
    echo "To push to Docker Hub:"
    echo "  1. Create repository on Docker Hub: https://hub.docker.com/repositories"
    echo "  2. Login: docker login"
    echo "  3. Run: ./build.sh ${VERSION} true"
fi

