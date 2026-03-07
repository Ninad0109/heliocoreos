#!/bin/bash
set -e

echo "=== HelioCore OS Farm-Pi Setup ==="

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python dependencies
cd farm-node
pip3 install -r requirements.txt

# Enable I2C and SPI (if needed)
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# Create systemd service
sudo cp ../install/farm.service /etc/systemd/system/heliocore-farm.service
sudo systemctl daemon-reload
sudo systemctl enable heliocore-farm.service

echo "=== Farm-Pi Setup Complete ==="
echo "Update config.json with Master-Pi IP address"
echo "Start farm node: sudo systemctl start heliocore-farm"
