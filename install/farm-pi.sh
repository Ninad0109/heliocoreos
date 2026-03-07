#!/bin/bash
# ============================================================
# HelioCore OS — Farm-Pi Setup Script
# Run: sudo bash install/farm-pi.sh
# ============================================================
set -e

HELIO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HELIO_USER="${SUDO_USER:-pi}"
HELIO_HOME="/home/${HELIO_USER}/heliocoreos"

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║     HelioCore OS — Farm-Pi Setup                  ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# ----------------------------------------------------------
# 0. Pre-flight: check config
# ----------------------------------------------------------
CONFIG_FILE="${HELIO_DIR}/farm-node/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] Config file not found: ${CONFIG_FILE}"
    exit 1
fi

MASTER_IP=$(python3 -c "import json; print(json.load(open('${CONFIG_FILE}'))['master_ip'])")
echo "[CHECK] Master-Pi IP configured as: ${MASTER_IP}"
echo "        If this is wrong, edit farm-node/config.json and re-run."
echo ""
read -p "Continue with this IP? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted. Edit farm-node/config.json first."
    exit 1
fi

# ----------------------------------------------------------
# 1. System update
# ----------------------------------------------------------
echo "[1/7] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
echo "  ✓ System updated"

# ----------------------------------------------------------
# 2. Install system dependencies
# ----------------------------------------------------------
echo "[2/7] Installing system dependencies..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-rpi.gpio \
    curl \
    git
echo "  ✓ System dependencies installed"

# ----------------------------------------------------------
# 3. Install Python dependencies
# ----------------------------------------------------------
echo "[3/7] Installing Python packages..."
pip3 install --break-system-packages \
    RPi.GPIO==0.7.1 \
    requests==2.31.0 \
    psutil==5.9.0 \
    prompt-toolkit==3.0.36 \
    2>/dev/null || \
pip3 install \
    RPi.GPIO==0.7.1 \
    requests==2.31.0 \
    psutil==5.9.0 \
    prompt-toolkit==3.0.36
echo "  ✓ Python packages installed"

# ----------------------------------------------------------
# 4. Enable GPIO interfaces
# ----------------------------------------------------------
echo "[4/7] Enabling GPIO interfaces..."
if command -v raspi-config &> /dev/null; then
    raspi-config nonint do_i2c 0 2>/dev/null || true
    raspi-config nonint do_spi 0 2>/dev/null || true
    echo "  ✓ I2C and SPI enabled"
else
    echo "  ⚠ raspi-config not found, skip GPIO config"
fi

# ----------------------------------------------------------
# 5. Create runtime directories
# ----------------------------------------------------------
echo "[5/7] Creating runtime directories..."
mkdir -p /tmp/heliocore/pids
mkdir -p /tmp/heliocore/logs
chown -R ${HELIO_USER}:${HELIO_USER} /tmp/heliocore

# Ensure /tmp/heliocore survives reboot
cat > /etc/tmpfiles.d/heliocore.conf << EOF
d /tmp/heliocore 0755 ${HELIO_USER} ${HELIO_USER} -
d /tmp/heliocore/pids 0755 ${HELIO_USER} ${HELIO_USER} -
d /tmp/heliocore/logs 0755 ${HELIO_USER} ${HELIO_USER} -
EOF
echo "  ✓ Runtime directories created (persist across reboot)"

# ----------------------------------------------------------
# 6. Install systemd services
# ----------------------------------------------------------
echo "[6/7] Installing systemd services..."

# Farm node main service (runs boot → shell)
cat > /etc/systemd/system/heliocore-farm.service << EOF
[Unit]
Description=HelioCore OS Farm Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${HELIO_DIR}
ExecStart=/usr/bin/python3 ${HELIO_DIR}/farm-node/farm_node.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=${HELIO_DIR}
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Node agent service (registers with Master-Pi)
cat > /etc/systemd/system/heliocore-agent.service << EOF
[Unit]
Description=HelioCore OS Node Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${HELIO_USER}
WorkingDirectory=${HELIO_DIR}/farm-node
ExecStart=/usr/bin/python3 ${HELIO_DIR}/farm-node/node_agent.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=${HELIO_DIR}
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable heliocore-farm.service
systemctl enable heliocore-agent.service
echo "  ✓ Systemd services installed and enabled"

# ----------------------------------------------------------
# 7. Create CLI symlink
# ----------------------------------------------------------
echo "[7/7] Setting up CLI..."
cat > /usr/local/bin/heliocore << 'SCRIPT'
#!/bin/bash
export PYTHONPATH="${HELIO_DIR}:${PYTHONPATH}"
python3 "${HELIO_DIR}/core/heliocore_cli.py" "$@"
SCRIPT

sed -i "s|\${HELIO_DIR}|${HELIO_DIR}|g" /usr/local/bin/heliocore
chmod +x /usr/local/bin/heliocore
echo "  ✓ CLI available as 'heliocore' command"

# ----------------------------------------------------------
# 8. Test connectivity to Master-Pi
# ----------------------------------------------------------
echo ""
echo "[TEST] Testing connection to Master-Pi at ${MASTER_IP}..."
if ping -c 1 -W 3 ${MASTER_IP} &> /dev/null; then
    echo "  ✓ Master-Pi is reachable"

    # Try telemetry endpoint
    if curl -s --connect-timeout 3 "http://${MASTER_IP}:5000/status" &> /dev/null; then
        echo "  ✓ Telemetry server responding"
    else
        echo "  ⚠ Telemetry server not responding (start it on Master-Pi first)"
    fi

    # Try node registry
    if curl -s --connect-timeout 3 "http://${MASTER_IP}:5001/node/list" &> /dev/null; then
        echo "  ✓ Node registry responding"
    else
        echo "  ⚠ Node registry not responding (start it on Master-Pi first)"
    fi
else
    echo "  ⚠ Master-Pi not reachable — check network and config.json"
fi

# ----------------------------------------------------------
# Done
# ----------------------------------------------------------
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║     Farm-Pi Setup Complete!                       ║"
echo "╠═══════════════════════════════════════════════════╣"
echo "║                                                   ║"
echo "║  Services installed (start on next boot):         ║"
echo "║    • heliocore-farm   (sensor/motor/tracking)     ║"
echo "║    • heliocore-agent  (node registration)         ║"
echo "║                                                   ║"
echo "║  Start now:                                       ║"
echo "║    sudo systemctl start heliocore-farm             ║"
echo "║    sudo systemctl start heliocore-agent            ║"
echo "║                                                   ║"
echo "║  Or boot the full OS:                             ║"
echo "║    sudo python3 core/init.py                      ║"
echo "║                                                   ║"
echo "║  Test hardware:                                   ║"
echo "║    python3 farm-node/sensor_manager.py             ║"
echo "║    sudo python3 farm-node/motor_controller.py      ║"
echo "║                                                   ║"
echo "║  GPIO pins configured:                            ║"
echo "║    LDR:   17, 27, 22, 23, 24, 25                  ║"
echo "║    Rain:  5, 6                                     ║"
echo "║    Motor: STEP/DIR 12/16, 20/21, 13/19             ║"
echo "║                                                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""
echo "IMPORTANT: Wire all sensors and motors before starting services."
echo ""
