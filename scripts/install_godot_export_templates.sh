#!/bin/bash

# Install Godot Export Templates

set -e

GODOT_VERSION=${1:-"4.5-stable"}
# Convert version format from 4.5-stable to 4.5.stable for Godot's expected path
GODOT_TEMPLATE_VERSION=$(echo "$GODOT_VERSION" | sed 's/-/./g')
TEMPLATES_DIR="/root/.local/share/godot/export_templates/${GODOT_TEMPLATE_VERSION}"

# Check if templates are already installed
if [ -d "$TEMPLATES_DIR" ] && [ "$(ls -A "$TEMPLATES_DIR" 2>/dev/null)" ] && [ "${FORCE_INSTALL:-false}" != "true" ]; then
    echo "✅ Godot ${GODOT_VERSION} export templates already installed at ${TEMPLATES_DIR}"
    echo "Skipping installation. Set FORCE_INSTALL=true to reinstall."
    exit 0
fi

echo "Installing Godot ${GODOT_VERSION} export templates..."

# Create templates directory
mkdir -p "$TEMPLATES_DIR"

# Download and install export templates
cd /tmp
echo "Downloading export templates..."
wget -v https://github.com/godotengine/godot-builds/releases/download/${GODOT_VERSION}/Godot_v${GODOT_VERSION}_export_templates.tpz

echo "Checking downloaded file..."
ls -la Godot_v${GODOT_VERSION}_export_templates.tpz

echo "Extracting export templates..."
unzip -o Godot_v${GODOT_VERSION}_export_templates.tpz

echo "Checking extracted contents..."
ls -la /tmp/

echo "Installing templates to ${TEMPLATES_DIR}..."
if [ -d "templates" ]; then
    mv templates/* "$TEMPLATES_DIR/"
else
    echo "ERROR: templates directory not found after extraction"
    ls -la /tmp/
    exit 1
fi

echo "Cleaning up..."
rm -rf templates Godot_v${GODOT_VERSION}_export_templates.tpz

echo "Verifying installation..."
ls -la "$TEMPLATES_DIR/"

echo "✅ Godot ${GODOT_VERSION} export templates installed successfully!"
