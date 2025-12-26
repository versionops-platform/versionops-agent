#!/bin/bash
# Build script for VersionOps Agent
# Creates standalone binaries for Linux amd64 and arm64

set -e

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/dist"
AGENT_SCRIPT="$SCRIPT_DIR/versionops_agent.py"

echo "🔧 VersionOps Agent Build Script v$VERSION"
echo "=========================================="

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  Warning: Building on non-Linux system. For cross-platform builds, use Docker."
fi

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required"
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$BUILD_DIR" "$SCRIPT_DIR/build" "$SCRIPT_DIR/*.spec"

# Build binary
echo "🔨 Building binary..."
ARCH=$(uname -m)
case $ARCH in
    x86_64) ARCH_NAME="amd64" ;;
    aarch64|arm64) ARCH_NAME="arm64" ;;
    *) ARCH_NAME="$ARCH" ;;
esac

pyinstaller \
    --onefile \
    --name "versionops-agent-linux-$ARCH_NAME" \
    --clean \
    --noconfirm \
    "$AGENT_SCRIPT"

# Make executable
chmod +x "$BUILD_DIR/versionops-agent-linux-$ARCH_NAME"

echo ""
echo "✅ Build complete!"
echo "   Binary: $BUILD_DIR/versionops-agent-linux-$ARCH_NAME"
echo "   Size: $(du -h "$BUILD_DIR/versionops-agent-linux-$ARCH_NAME" | cut -f1)"
echo ""
echo "To test: $BUILD_DIR/versionops-agent-linux-$ARCH_NAME version"
