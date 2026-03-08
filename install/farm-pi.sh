#!/bin/bash
# ============================================================
# HelioCore OS — Farm-Pi Production Setup
# Run: sudo bash install/farm-pi.sh
#
# Installs: hardware services, CLI shell, and auto-boot system
# The Farm-Pi shows HelioCore OS terminal with logs on boot.
# ============================================================
set -e

HELIO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HELIO_USER="${SUDO_USER:-pi}"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     HelioCore OS — Farm-Pi Setup                        ║"
echo "╚════════════════════════════════════════════════════════╝"
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
echo "[CHECK] Master-Pi IP: ${MASTER_IP}"
echo "        If wrong, edit farm-node/config.json and re-run."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
[[ ! $REPLY =~ ^[Yy]$ ]] && { echo "Aborted."; exit 1; }

# ----------------------------------------------------------
# 1. System update & dependencies
# ----------------------------------------------------------
echo "[1/8] Updating system and installing dependencies..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-rpi.gpio \
    curl git
echo "  ✓ System dependencies installed"

# ----------------------------------------------------------
# 2. Python packages
# ----------------------------------------------------------
echo "[2/8] Installing Python packages..."
pip3 install --break-system-packages \
    RPi.GPIO==0.7.1 requests==2.31.0 \
    psutil==5.9.0 prompt-toolkit==3.0.36 \
    2>/dev/null || \
pip3 install \
    RPi.GPIO==0.7.1 requests==2.31.0 \
    psutil==5.9.0 prompt-toolkit==3.0.36
echo "  ✓ Python packages installed"

# ----------------------------------------------------------
# 3. Enable GPIO interfaces
# ----------------------------------------------------------
echo "[3/8] Enabling GPIO interfaces..."
if command -v raspi-config &> /dev/null; then
    raspi-config nonint do_i2c 0 2>/dev/null || true
    raspi-config nonint do_spi 0 2>/dev/null || true
    echo "  ✓ I2C and SPI enabled"
else
    echo "  ⚠ raspi-config not found, skipping"
fi

# ----------------------------------------------------------
# 4. Create runtime directories
# ----------------------------------------------------------
echo "[4/8] Creating runtime directories..."
mkdir -p /tmp/heliocore/pids /tmp/heliocore/logs
chown -R ${HELIO_USER}:${HELIO_USER} /tmp/heliocore

cat > /etc/tmpfiles.d/heliocore.conf << EOF
d /tmp/heliocore 0755 ${HELIO_USER} ${HELIO_USER} -
d /tmp/heliocore/pids 0755 ${HELIO_USER} ${HELIO_USER} -
d /tmp/heliocore/logs 0755 ${HELIO_USER} ${HELIO_USER} -
EOF
echo "  ✓ Runtime directories (persist across reboot)"

# ----------------------------------------------------------
# 5. Install systemd services
# ----------------------------------------------------------
echo "[5/8] Installing systemd services..."

# Main farm node service (hardware control loop)
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
StandardOutput=append:/tmp/heliocore/logs/farm.log
StandardError=append:/tmp/heliocore/logs/farm.log

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
StandardOutput=append:/tmp/heliocore/logs/agent.log
StandardError=append:/tmp/heliocore/logs/agent.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable heliocore-farm heliocore-agent
echo "  ✓ Services installed and enabled (auto-start on boot)"

# ----------------------------------------------------------
# 6. CLI symlink
# ----------------------------------------------------------
echo "[6/8] Setting up CLI..."
cat > /usr/local/bin/heliocore << 'SCRIPT'
#!/bin/bash
export PYTHONPATH="${HELIO_DIR}:${PYTHONPATH}"
python3 "${HELIO_DIR}/core/heliocore_cli.py" "$@"
SCRIPT
sed -i "s|\${HELIO_DIR}|${HELIO_DIR}|g" /usr/local/bin/heliocore
chmod +x /usr/local/bin/heliocore
echo "  ✓ CLI: 'heliocore' command"

# ----------------------------------------------------------
# 7. Auto-login with HelioCore OS shell
# ----------------------------------------------------------
echo "[7/8] Configuring auto-login with HelioCore OS shell..."

# Create HelioCore OS login script
cat > /usr/local/bin/heliocore-shell << SHELL
#!/bin/bash
# HelioCore OS — Terminal UI
export PYTHONPATH="${HELIO_DIR}:\${PYTHONPATH}"

echo ""
echo "  ██╗  ██╗███████╗██╗     ██╗ ██████╗  ██████╗ ██████╗ ██████╗ ███████╗"
echo "  ██║  ██║██╔════╝██║     ██║██╔═══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝"
echo "  ███████║█████╗  ██║     ██║██║   ██║██║     ██║   ██║██████╔╝█████╗  "
echo "  ██╔══██║██╔══╝  ██║     ██║██║   ██║██║     ██║   ██║██╔══██╗██╔══╝  "
echo "  ██║  ██║███████╗███████╗██║╚██████╔╝╚██████╗╚██████╔╝██║  ██║███████╗"
echo "  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
echo ""
echo "  HelioCore OS v1.0 — Solar Tracking System"
echo "  Node: \$(hostname) | Master: ${MASTER_IP}"
echo ""
echo "  Services:"
systemctl is-active heliocore-farm > /dev/null 2>&1 && echo "    ✅ Farm Node (sensors/motors)" || echo "    ❌ Farm Node"
systemctl is-active heliocore-agent > /dev/null 2>&1 && echo "    ✅ Node Agent (registration)" || echo "    ❌ Node Agent"
echo ""
echo "  Logs:    journalctl -u heliocore-farm -f"
echo "  Status:  heliocore status"
echo "  Shell:   python3 ${HELIO_DIR}/core/init.py"
echo ""

# Start the interactive HelioCore shell
python3 ${HELIO_DIR}/core/init.py 2>/dev/null || {
    echo "  [FALLBACK] Interactive shell failed, dropping to bash"
    exec /bin/bash
}
SHELL
chmod +x /usr/local/bin/heliocore-shell

# Configure auto-login to TTY1
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ${HELIO_USER} --noclear %I \$TERM
EOF

# Add HelioCore shell to .bashrc for auto-launch on login
BASHRC="/home/${HELIO_USER}/.bashrc"
if ! grep -q "heliocore-shell" "${BASHRC}" 2>/dev/null; then
    echo "" >> "${BASHRC}"
    echo "# HelioCore OS — auto-launch on TTY login" >> "${BASHRC}"
    echo "if [ -z \"\$SSH_CONNECTION\" ] && [ \"\$(tty)\" = \"/dev/tty1\" ]; then" >> "${BASHRC}"
    echo "    /usr/local/bin/heliocore-shell" >> "${BASHRC}"
    echo "fi" >> "${BASHRC}"
fi
echo "  ✓ Auto-login configured (TTY1 → HelioCore OS shell)"

# ----------------------------------------------------------
# 8. Test connectivity & start services
# ----------------------------------------------------------
echo "[8/8] Testing and starting services..."

# Start services now
systemctl start heliocore-farm 2>/dev/null || echo "  ⚠ Farm service needs hardware (will start on Pi)"
systemctl start heliocore-agent 2>/dev/null || true

# Test Master-Pi connectivity
echo ""
echo "  Testing Master-Pi connection (${MASTER_IP})..."
if ping -c 1 -W 3 ${MASTER_IP} &> /dev/null; then
    echo "  ✓ Master-Pi is reachable"
    curl -s --connect-timeout 3 "http://${MASTER_IP}:5000/status" > /dev/null 2>&1 && \
        echo "  ✓ Telemetry server responding" || \
        echo "  ⚠ Telemetry server not responding (start Master-Pi first)"
    curl -s --connect-timeout 3 "http://${MASTER_IP}:5001/node/list" > /dev/null 2>&1 && \
        echo "  ✓ Node registry responding" || \
        echo "  ⚠ Node registry not responding (start Master-Pi first)"
else
    echo "  ⚠ Master-Pi not reachable — check network and config.json"
fi

# ----------------------------------------------------------
# Done
# ----------------------------------------------------------
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅  Farm-Pi Setup Complete!                            ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  On boot:                                              ║"
echo "║    → Auto-login → HelioCore OS terminal                ║"
echo "║    → Farm service starts (sensors + motors)            ║"
echo "║    → Node agent registers with Master-Pi               ║"
echo "║                                                        ║"
echo "║  Logs:                                                 ║"
echo "║    journalctl -u heliocore-farm -f                     ║"
echo "║    cat /tmp/heliocore/logs/farm.log                    ║"
echo "║                                                        ║"
echo "║  Commands:                                             ║"
echo "║    heliocore status    — System status                 ║"
echo "║    heliocore health    — Health check                  ║"
echo "║    heliocore logs      — View logs                     ║"
echo "║                                                        ║"
echo "║  Hardware test:                                        ║"
echo "║    python3 farm-node/sensor_manager.py                 ║"
echo "║    sudo python3 farm-node/motor_controller.py          ║"
echo "║                                                        ║"
echo "║  GPIO pins:                                            ║"
echo "║    LDR:   6 (LB), 26 (LT), 17 (RT), 5 (RB)           ║"
echo "║    Rain:  15                                           ║"
echo "║    Base:  STEP=12 DIR=4                                ║"
echo "║    Tilt:  STEP=13 DIR=19                               ║"
echo "║    Petal: STEP=27 DIR=18                               ║"
echo "║                                                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "IMPORTANT: Wire all sensors and motors before rebooting."
echo "Reboot now: sudo reboot"
echo ""
