#!/bin/bash
set -e

echo "=== HelioCore OS Master-Pi Setup ==="

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python dependencies
cd master-node
pip3 install -r requirements.txt

# Install Grafana
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install -y grafana

# Enable Grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

# Create systemd service for telemetry server
sudo cp ../install/master.service /etc/systemd/system/heliocore-master.service
sudo systemctl daemon-reload
sudo systemctl enable heliocore-master.service

echo "=== Master-Pi Setup Complete ==="
echo "Telemetry server: sudo systemctl start heliocore-master"
echo "HelioCore CLI: python3 heliocore_os.py"
echo "Grafana: http://localhost:3000 (admin/admin)"
