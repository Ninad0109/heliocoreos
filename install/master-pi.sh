#!/bin/bash
# ============================================================
# HelioCore OS — Master-Pi Production Setup
# Run: sudo bash install/master-pi.sh
#
# Installs: telemetry server, node registry, Prometheus, Grafana
# All services auto-start on boot via systemd.
# ============================================================
set -e

HELIO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HELIO_USER="${SUDO_USER:-pi}"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     HelioCore OS — Master-Pi Setup                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# ----------------------------------------------------------
# 1. System update & dependencies
# ----------------------------------------------------------
echo "[1/8] Updating system and installing dependencies..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    curl wget git \
    apt-transport-https software-properties-common
echo "  ✓ System dependencies installed"

# ----------------------------------------------------------
# 2. Python packages
# ----------------------------------------------------------
echo "[2/8] Installing Python packages..."
pip3 install --break-system-packages \
    flask==2.3.0 werkzeug==2.3.0 \
    requests==2.31.0 psutil==5.9.0 \
    prompt-toolkit==3.0.36 \
    2>/dev/null || \
pip3 install \
    flask==2.3.0 werkzeug==2.3.0 \
    requests==2.31.0 psutil==5.9.0 \
    prompt-toolkit==3.0.36
echo "  ✓ Python packages installed"

# ----------------------------------------------------------
# 3. Install Grafana (via apt)
# ----------------------------------------------------------
echo "[3/8] Installing Grafana..."
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
echo "  ✓ Grafana enabled (http://localhost:3000)"

# ----------------------------------------------------------
# 4. Install Prometheus
# ----------------------------------------------------------
echo "[4/8] Installing Prometheus..."
ARCH=$(uname -m)
case $ARCH in
    aarch64) PROM_ARCH="linux-arm64" ;;
    armv7l)  PROM_ARCH="linux-armv7" ;;
    x86_64)  PROM_ARCH="linux-amd64" ;;
esac
PROM_VER="2.51.0"
PROM_DIR="/opt/prometheus"

if [ ! -f "${PROM_DIR}/prometheus" ]; then
    mkdir -p /opt
    PROM_URL="https://github.com/prometheus/prometheus/releases/download/v${PROM_VER}/prometheus-${PROM_VER}.${PROM_ARCH}.tar.gz"
    curl -sL "${PROM_URL}" | tar xz -C /opt
    mv "/opt/prometheus-${PROM_VER}.${PROM_ARCH}" "${PROM_DIR}"
    echo "  ✓ Prometheus ${PROM_VER} installed"
else
    echo "  ✓ Prometheus already installed"
fi

# Prometheus config
cat > "${PROM_DIR}/heliocore.yml" <<PROMCFG
global:
  scrape_interval: 2s
  evaluation_interval: 2s

scrape_configs:
  - job_name: 'heliocore'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 2s
PROMCFG

# Prometheus systemd service
cat > /etc/systemd/system/prometheus.service << EOF
[Unit]
Description=Prometheus Metrics Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=${PROM_DIR}/prometheus \\
    --config.file=${PROM_DIR}/heliocore.yml \\
    --web.listen-address=:9090 \\
    --storage.tsdb.path=/var/lib/prometheus
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /var/lib/prometheus
systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus
echo "  ✓ Prometheus enabled (http://localhost:9090)"

# ----------------------------------------------------------
# 5. Create runtime directories
# ----------------------------------------------------------
echo "[5/8] Creating runtime directories..."
mkdir -p /tmp/heliocore/pids /tmp/heliocore/logs
chown -R ${HELIO_USER}:${HELIO_USER} /tmp/heliocore

# Persist across reboot
cat > /etc/tmpfiles.d/heliocore.conf << EOF
d /tmp/heliocore 0755 ${HELIO_USER} ${HELIO_USER} -
d /tmp/heliocore/pids 0755 ${HELIO_USER} ${HELIO_USER} -
d /tmp/heliocore/logs 0755 ${HELIO_USER} ${HELIO_USER} -
EOF
echo "  ✓ Runtime directories created"

# ----------------------------------------------------------
# 6. Install systemd services for HelioCore
# ----------------------------------------------------------
echo "[6/8] Installing HelioCore systemd services..."

# Telemetry server
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

# Node registry
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
systemctl enable heliocore-telemetry heliocore-registry
systemctl start heliocore-telemetry heliocore-registry
echo "  ✓ Telemetry server + Node registry enabled"

# ----------------------------------------------------------
# 7. Import Grafana dashboard
# ----------------------------------------------------------
echo "[7/8] Importing Grafana dashboard..."
sleep 5  # Wait for Grafana to be ready

# Add Prometheus datasource
python3 -c "
import requests, time
for i in range(15):
    try:
        requests.get('http://localhost:3000/api/health', timeout=2)
        break
    except:
        time.sleep(2)

try:
    r = requests.post('http://localhost:3000/api/datasources',
        auth=('admin','admin'), timeout=10,
        json={'name':'Prometheus','type':'prometheus','url':'http://localhost:9090','access':'proxy','isDefault':True})
    print(f'  Datasource: {\"added\" if r.ok else \"exists\"} ')
except Exception as e:
    print(f'  Datasource warning: {e}')
"

# Import dashboard
python3 "${HELIO_DIR}/dashboards/import_dashboard.py" 2>/dev/null || echo "  ⚠ Dashboard import deferred (run manually later)"
echo "  ✓ Dashboard provisioned"

# ----------------------------------------------------------
# 8. CLI symlink
# ----------------------------------------------------------
echo "[8/8] Setting up CLI..."
cat > /usr/local/bin/heliocore << 'SCRIPT'
#!/bin/bash
export PYTHONPATH="${HELIO_DIR}:${PYTHONPATH}"
python3 "${HELIO_DIR}/core/heliocore_cli.py" "$@"
SCRIPT
sed -i "s|\${HELIO_DIR}|${HELIO_DIR}|g" /usr/local/bin/heliocore
chmod +x /usr/local/bin/heliocore
echo "  ✓ CLI: 'heliocore' command"

# ----------------------------------------------------------
# Verify
# ----------------------------------------------------------
echo ""
echo "Verifying services..."
systemctl is-active heliocore-telemetry > /dev/null && echo "  ✓ heliocore-telemetry" || echo "  ✗ heliocore-telemetry"
systemctl is-active heliocore-registry > /dev/null && echo "  ✓ heliocore-registry" || echo "  ✗ heliocore-registry"
systemctl is-active prometheus > /dev/null && echo "  ✓ prometheus" || echo "  ✗ prometheus"
systemctl is-active grafana-server > /dev/null && echo "  ✓ grafana-server" || echo "  ✗ grafana-server"

LOCAL_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅  Master-Pi Setup Complete!                          ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  Services (auto-start on boot):                        ║"
echo "║    📊 Grafana          → http://${LOCAL_IP}:3000         ║"
echo "║    🔍 Prometheus       → http://${LOCAL_IP}:9090         ║"
echo "║    📡 Telemetry server → http://${LOCAL_IP}:5000         ║"
echo "║    📋 Node registry    → http://${LOCAL_IP}:5001         ║"
echo "║                                                        ║"
echo "║  Grafana login: admin / admin                          ║"
echo "║  Dashboard: http://${LOCAL_IP}:3000/d/heliocore-obs      ║"
echo "║                                                        ║"
echo "║  Now run on Farm-Pi:                                   ║"
echo "║    sudo bash install/farm-pi.sh                        ║"
echo "║                                                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
