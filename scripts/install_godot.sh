#!/bin/bash

# Godot Installation Script for Ubuntu

set -e

GODOT_VERSION=${1:-"4.5-rc2"}

echo "Installing Godot $GODOT_VERSION..."

# Install dependencies
apt-get update
apt-get install -y wget unzip libfontconfig1

# Download and install Godot (detect architecture)
cd /tmp
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Map architecture to Godot build
if [ "$ARCH" = "x86_64" ]; then
    GODOT_FILE="Godot_v${GODOT_VERSION}_linux.x86_64.zip"
    GODOT_BINARY="Godot_v${GODOT_VERSION}_linux.x86_64"
elif [ "$ARCH" = "aarch64" ]; then
    GODOT_FILE="Godot_v${GODOT_VERSION}_linux.arm64.zip"
    GODOT_BINARY="Godot_v${GODOT_VERSION}_linux.arm64"
else
    echo "❌ Unsupported architecture: $ARCH"
    exit 1
fi

echo "Downloading Godot $GODOT_VERSION for $ARCH..."
wget --progress=bar --timeout=30 https://github.com/godotengine/godot-builds/releases/download/${GODOT_VERSION}/$GODOT_FILE
if [ $? -ne 0 ]; then
    echo "❌ Failed to download Godot. Trying alternative URL..."
    wget --progress=bar --timeout=30 https://downloads.tuxfamily.org/godotengine/${GODOT_VERSION}/$GODOT_FILE
fi

unzip $GODOT_FILE
mv $GODOT_BINARY /usr/local/bin/godot
chmod +x /usr/local/bin/godot
rm $GODOT_FILE

echo "✅ Godot $GODOT_VERSION installed successfully!"
godot --version
