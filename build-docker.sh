#!/bin/bash
# Build VersionOps Agent for multiple architectures using Docker
# This allows cross-compilation from any host OS
# Uses python:3.11-slim-bullseye for glibc 2.31 compatibility (works on most Linux distros)

set -e

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/dist"

# Use Debian Bullseye (glibc 2.31) for maximum compatibility
# Works on: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, Amazon Linux 2
BASE_IMAGE="python:3.11-slim-bullseye"

echo "🐳 VersionOps Agent Docker Build v$VERSION"
echo "==========================================="
echo "Base image: $BASE_IMAGE (glibc 2.31)"

# Clean previous builds
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build for AMD64
echo ""
echo "🔨 Building for linux-amd64..."
docker run --rm -v "$SCRIPT_DIR:/src" -w /src \
    --platform linux/amd64 \
    $BASE_IMAGE \
    bash -c "
        apt-get update -qq && apt-get install -y -qq binutils > /dev/null && \
        pip install -q pyinstaller requests && \
        pyinstaller --onefile --name versionops-agent-linux-amd64 --clean --noconfirm versionops_agent.py && \
        chmod +x dist/versionops-agent-linux-amd64
    "

echo "✅ Built: dist/versionops-agent-linux-amd64"

# Build for ARM64
echo ""
echo "🔨 Building for linux-arm64..."
docker run --rm -v "$SCRIPT_DIR:/src" -w /src \
    --platform linux/arm64 \
    $BASE_IMAGE \
    bash -c "
        apt-get update -qq && apt-get install -y -qq binutils > /dev/null && \
        pip install -q pyinstaller requests && \
        pyinstaller --onefile --name versionops-agent-linux-arm64 --clean --noconfirm versionops_agent.py && \
        chmod +x dist/versionops-agent-linux-arm64
    "

echo "✅ Built: dist/versionops-agent-linux-arm64"

# Cleanup PyInstaller artifacts
rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR"/*.spec

echo ""
echo "=========================================="
echo "✅ All builds complete!"
echo ""
ls -lh "$BUILD_DIR/"
echo ""
echo "Next steps:"
echo "  1. Upload binaries to GitHub Releases"
echo "  2. Update install script with download URLs"
