#!/bin/bash
# ============================================================
# HelioCore OS — Master-Pi Setup Script
# Run: sudo bash install/master-pi.sh
# ============================================================
set -e

HELIO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HELIO_USER="${SUDO_USER:-pi}"
HELIO_HOME="/home/${HELIO_USER}/heliocoreos"

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║     HelioCore OS — Master-Pi Setup                ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

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
    curl \
    wget \
    git \
    apt-transport-https \
    software-properties-common
echo "  ✓ System dependencies installed"

# ----------------------------------------------------------
# 3. Install Python dependencies
# ----------------------------------------------------------
echo "[3/7] Installing Python packages..."
pip3 install --break-system-packages \
    flask==2.3.0 \
    requests==2.31.0 \
    psutil==5.9.0 \
    prompt-toolkit==3.0.36 \
    2>/dev/null || \
pip3 install \
    flask==2.3.0 \
    requests==2.31.0 \
    psutil==5.9.0 \
    prompt-toolkit==3.0.36
echo "  ✓ Python packages installed"

# ----------------------------------------------------------
# 4. Install Grafana
# ----------------------------------------------------------
echo "[4/7] Installing Grafana..."
if ! command -v grafana-server &> /dev/null; then
    wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key
    echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" \
        | tee /etc/apt/sources.list.d/grafana.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq grafana
    echo "  ✓ Grafana installed"
else
    echo "  ✓ Grafana already installed"
fi

systemctl daemon-reload
systemctl enable grafana-server
systemctl start grafana-server
echo "  ✓ Grafana enabled and started"

# ----------------------------------------------------------
# 5. Create runtime directories
# ----------------------------------------------------------
echo "[5/7] Creating runtime directories..."
mkdir -p /tmp/heliocore/pids
mkdir -p /tmp/heliocore/logs
chown -R ${HELIO_USER}:${HELIO_USER} /tmp/heliocore
echo "  ✓ Runtime directories created"

# ----------------------------------------------------------
# 6. Install systemd services
# ----------------------------------------------------------
echo "[6/7] Installing systemd services..."

# Telemetry server service
cat > /etc/systemd/system/heliocore-telemetry.service << EOF
[Unit]
Description=HelioCore OS Telemetry Server
After=network.target

[Service]
Type=simple
User=${HELIO_USER}
WorkingDirectory=${HELIO_DIR}/master-node
ExecStart=/usr/bin/python3 ${HELIO_DIR}/master-node/telemetry_server.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Node registry service
cat > /etc/systemd/system/heliocore-registry.service << EOF
[Unit]
Description=HelioCore OS Node Registry
After=network.target

[Service]
Type=simple
User=${HELIO_USER}
WorkingDirectory=${HELIO_DIR}/master-node
ExecStart=/usr/bin/python3 ${HELIO_DIR}/master-node/node_registry.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable heliocore-telemetry.service
systemctl enable heliocore-registry.service
systemctl start heliocore-telemetry.service
systemctl start heliocore-registry.service
echo "  ✓ Systemd services installed and started"

# ----------------------------------------------------------
# 7. Create CLI symlink
# ----------------------------------------------------------
echo "[7/7] Setting up CLI..."
cat > /usr/local/bin/heliocore << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")/../heliocoreos" 2>/dev/null || true
export PYTHONPATH="${HELIO_DIR}:${PYTHONPATH}"
python3 "${HELIO_DIR}/core/heliocore_cli.py" "$@"
SCRIPT

# Replace placeholder with actual path
sed -i "s|\${HELIO_DIR}|${HELIO_DIR}|g" /usr/local/bin/heliocore
chmod +x /usr/local/bin/heliocore
echo "  ✓ CLI available as 'heliocore' command"

# ----------------------------------------------------------
# Done
# ----------------------------------------------------------
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║     Master-Pi Setup Complete!                     ║"
echo "╠═══════════════════════════════════════════════════╣"
echo "║                                                   ║"
echo "║  Services running:                                ║"
echo "║    • Telemetry server  → http://localhost:5000     ║"
echo "║    • Node registry     → http://localhost:5001     ║"
echo "║    • Grafana dashboard → http://localhost:3000     ║"
echo "║                                                   ║"
echo "║  Grafana login: admin / admin                     ║"
echo "║                                                   ║"
echo "║  Commands:                                        ║"
echo "║    heliocore service status                       ║"
echo "║    heliocore node list                            ║"
echo "║    heliocore logs                                 ║"
echo "║    heliocore health                               ║"
echo "║    python3 master-node/heliocore_os.py  (CLI UI)  ║"
echo "║                                                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""
