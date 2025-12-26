#!/bin/bash
# VersionOps Agent Installer
# Usage: curl -fsSL https://get.versionops.dev/install.sh | sudo bash

set -e

VERSION="1.0.0"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/versionops-agent"
BINARY_NAME="versionops-agent"

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
if [ "$OS" != "linux" ]; then
    echo "❌ This installer only supports Linux"
    exit 1
fi

echo "📦 Installing VersionOps Agent v$VERSION"
echo "   Architecture: $ARCH"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run with sudo: curl -fsSL https://get.versionops.dev/install.sh | sudo bash"
    exit 1
fi

# Download binary
DOWNLOAD_URL="https://github.com/versionops/agent/releases/download/v${VERSION}/versionops-agent-linux-${ARCH}"
echo "⬇️  Downloading from $DOWNLOAD_URL..."

if command -v curl &> /dev/null; then
    curl -fsSL "$DOWNLOAD_URL" -o "/tmp/$BINARY_NAME"
elif command -v wget &> /dev/null; then
    wget -q "$DOWNLOAD_URL" -O "/tmp/$BINARY_NAME"
else
    echo "❌ curl or wget is required"
    exit 1
fi

# Install binary
echo "📁 Installing to $INSTALL_DIR..."
chmod +x "/tmp/$BINARY_NAME"
mv "/tmp/$BINARY_NAME" "$INSTALL_DIR/$BINARY_NAME"

# Create config directory
mkdir -p "$CONFIG_DIR"

echo ""
echo "✅ VersionOps Agent installed successfully!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Configure the agent:"
echo "     sudo versionops-agent config --backend=https://app.versionops.io --token=YOUR_TOKEN"
echo ""
echo "  2. Install systemd service:"
echo "     sudo versionops-agent install"
echo ""
echo "  3. Start the agent:"
echo "     sudo systemctl enable --now versionops-agent"
echo ""
echo "  4. Check status:"
echo "     sudo versionops-agent status"
echo ""
