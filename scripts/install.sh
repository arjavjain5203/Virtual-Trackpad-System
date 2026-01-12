#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

echo "Installing Virtual Trackpad..."

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"

echo "Project Root: $PROJECT_ROOT"

# Install udev rules
echo "Installing udev rules..."
cp "$DIR/99-virtual-trackpad.rules" /etc/udev/rules.d/
udevadm control --reload-rules
udevadm trigger

# Setup Systemd Service
echo "Setting up systemd service..."
SERVICE_FILE="$DIR/virtual-trackpad.service"
cp "$SERVICE_FILE" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

echo "Installation Complete."
echo "To start the service: systemctl start virtual-trackpad"
echo "To enable on boot: systemctl enable virtual-trackpad"
echo "To check status: systemctl status virtual-trackpad"

# Check if 'input' group exists and add user if not?
# Usually 'input' group exists. Current user might need to be added.
# echo "Ensure your user is in the 'input' group if running non-root: sudo usermod -aG input \$USER"
