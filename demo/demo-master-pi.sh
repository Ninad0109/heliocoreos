#!/bin/bash
# ============================================================
# HelioCore OS — Demo Master-Pi
# Runs: telemetry server, node registry, Prometheus, Grafana
# Shows: Grafana dashboard with live metrics
#
# Usage:  bash demo/demo-master-pi.sh
# Stop:   bash demo/demo-master-pi.sh stop
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELIO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${HELIO_DIR}/.venv-master"
TOOLS_DIR="${HELIO_DIR}/tools"
PROM_DIR="${TOOLS_DIR}/prometheus-2.51.0.linux-arm64"
GRAF_DIR="${TOOLS_DIR}/grafana-v11.5.2"
PID_DIR="/tmp/heliocore/pids"
LOG_DIR="/tmp/heliocore/logs"

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    aarch64)  PROM_ARCH="linux-arm64"; GRAF_ARCH="linux-arm64" ;;
    armv7l)   PROM_ARCH="linux-armv7"; GRAF_ARCH="linux-armv7" ;;
    x86_64)   PROM_ARCH="linux-amd64"; GRAF_ARCH="linux-amd64" ;;
    *)        echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

PROM_VER="2.51.0"
GRAF_VER="11.5.2"
PROM_DIR="${TOOLS_DIR}/prometheus-${PROM_VER}.${PROM_ARCH}"
GRAF_DIR="${TOOLS_DIR}/grafana-v${GRAF_VER}"

# ----------------------------------------------------------
# Stop command
# ----------------------------------------------------------
if [ "$1" = "stop" ]; then
    echo "Stopping HelioCore demo services..."
    [ -f ${PID_DIR}/telemetry.pid ] && kill $(cat ${PID_DIR}/telemetry.pid) 2>/dev/null && echo "  ✓ Telemetry stopped"
    [ -f ${PID_DIR}/registry.pid ] && kill $(cat ${PID_DIR}/registry.pid) 2>/dev/null && echo "  ✓ Registry stopped"
    [ -f ${PID_DIR}/prometheus.pid ] && kill $(cat ${PID_DIR}/prometheus.pid) 2>/dev/null && echo "  ✓ Prometheus stopped"
    [ -f ${PID_DIR}/grafana.pid ] && kill $(cat ${PID_DIR}/grafana.pid) 2>/dev/null && echo "  ✓ Grafana stopped"
    rm -f ${PID_DIR}/*.pid
    echo "All stopped."
    exit 0
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     HelioCore OS — Master-Pi Demo                      ║"
echo "║     Grafana Dashboard + Prometheus + Telemetry          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# ----------------------------------------------------------
# 1. Virtual environment
# ----------------------------------------------------------
echo "[1/7] Setting up Python virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
    echo "  ✓ Created: ${VENV_DIR}"
else
    echo "  ✓ Already exists"
fi
source "${VENV_DIR}/bin/activate"
echo "  ✓ Activated"

# ----------------------------------------------------------
# 2. Install Python dependencies
# ----------------------------------------------------------
echo "[2/7] Installing Python packages..."
pip install --quiet --upgrade pip
pip install --quiet flask==2.3.0 werkzeug==2.3.0 requests==2.31.0 psutil==5.9.0
echo "  ✓ All packages installed"

# ----------------------------------------------------------
# 3. Download Prometheus + Grafana (if not present)
# ----------------------------------------------------------
echo "[3/7] Setting up Prometheus & Grafana..."
mkdir -p "${TOOLS_DIR}" "${PID_DIR}" "${LOG_DIR}"

# Prometheus
if [ ! -f "${PROM_DIR}/prometheus" ]; then
    echo "  Downloading Prometheus ${PROM_VER}..."
    PROM_URL="https://github.com/prometheus/prometheus/releases/download/v${PROM_VER}/prometheus-${PROM_VER}.${PROM_ARCH}.tar.gz"
    curl -sL "${PROM_URL}" | tar xz -C "${TOOLS_DIR}"
    echo "  ✓ Prometheus downloaded"
else
    echo "  ✓ Prometheus already present"
fi

# Grafana
if [ ! -f "${GRAF_DIR}/bin/grafana-server" ] && [ ! -f "${GRAF_DIR}/bin/grafana" ]; then
    echo "  Downloading Grafana ${GRAF_VER}..."
    GRAF_URL="https://dl.grafana.com/oss/release/grafana-${GRAF_VER}.${GRAF_ARCH}.tar.gz"
    curl -sL "${GRAF_URL}" | tar xz -C "${TOOLS_DIR}"
    echo "  ✓ Grafana downloaded"
else
    echo "  ✓ Grafana already present"
fi

# ----------------------------------------------------------
# 4. Write Prometheus config
# ----------------------------------------------------------
echo "[4/7] Configuring Prometheus..."
cat > "${PROM_DIR}/prometheus_heliocore.yml" <<PROMCFG
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
echo "  ✓ Config written"

# ----------------------------------------------------------
# 5. Kill previous instances & start services
# ----------------------------------------------------------
echo "[5/7] Starting services..."
pkill -f "telemetry_server.py" 2>/dev/null || true
pkill -f "node_registry.py" 2>/dev/null || true
pkill -f "prometheus" 2>/dev/null || true
pkill -f "grafana" 2>/dev/null || true
sleep 1

# Telemetry server
cd "${HELIO_DIR}/master-node"
python3 telemetry_server.py > "${LOG_DIR}/telemetry.log" 2>&1 &
echo $! > "${PID_DIR}/telemetry.pid"
sleep 2
if kill -0 $(cat "${PID_DIR}/telemetry.pid") 2>/dev/null; then
    echo "  ✓ Telemetry server     → http://localhost:5000"
else
    echo "  ✗ Telemetry server failed"; cat "${LOG_DIR}/telemetry.log"; exit 1
fi

# Node registry
python3 "${HELIO_DIR}/master-node/node_registry.py" > "${LOG_DIR}/registry.log" 2>&1 &
echo $! > "${PID_DIR}/registry.pid"
sleep 1
echo "  ✓ Node registry        → http://localhost:5001"

# Prometheus
"${PROM_DIR}/prometheus" \
    --config.file="${PROM_DIR}/prometheus_heliocore.yml" \
    --web.listen-address=":9090" \
    --storage.tsdb.path="${TOOLS_DIR}/prometheus-data" \
    > "${LOG_DIR}/prometheus.log" 2>&1 &
echo $! > "${PID_DIR}/prometheus.pid"
sleep 2
if kill -0 $(cat "${PID_DIR}/prometheus.pid") 2>/dev/null; then
    echo "  ✓ Prometheus           → http://localhost:9090"
else
    echo "  ✗ Prometheus failed"; cat "${LOG_DIR}/prometheus.log"; exit 1
fi

# Grafana
GRAFANA_BIN="${GRAF_DIR}/bin/grafana-server"
[ ! -f "$GRAFANA_BIN" ] && GRAFANA_BIN="${GRAF_DIR}/bin/grafana"
cd "${GRAF_DIR}"
"${GRAFANA_BIN}" > "${LOG_DIR}/grafana.log" 2>&1 &
echo $! > "${PID_DIR}/grafana.pid"
sleep 4
if kill -0 $(cat "${PID_DIR}/grafana.pid") 2>/dev/null; then
    echo "  ✓ Grafana              → http://localhost:3000"
else
    echo "  ✗ Grafana failed"; cat "${LOG_DIR}/grafana.log"; exit 1
fi

# ----------------------------------------------------------
# 6. Provision Grafana datasource + dashboard
# ----------------------------------------------------------
echo "[6/7] Importing Grafana dashboard..."
cd "${HELIO_DIR}"

# Wait for Grafana API
RETRIES=0
until curl -s http://localhost:3000/api/health > /dev/null 2>&1; do
    RETRIES=$((RETRIES + 1))
    [ $RETRIES -ge 15 ] && { echo "  ✗ Grafana API timeout"; exit 1; }
    sleep 1
done

python3 "${HELIO_DIR}/dashboards/import_dashboard.py"

# ----------------------------------------------------------
# 7. Verify
# ----------------------------------------------------------
echo "[7/7] Verifying all endpoints..."
curl -s http://localhost:5000/status > /dev/null 2>&1 && echo "  ✓ /status" || echo "  ✗ /status"
curl -s http://localhost:5000/metrics > /dev/null 2>&1 && echo "  ✓ /metrics ($(curl -s http://localhost:5000/metrics | wc -l) metrics)" || echo "  ✗ /metrics"
curl -s http://localhost:5001/node/list > /dev/null 2>&1 && echo "  ✓ /node/list" || echo "  ✗ /node/list"
curl -s http://localhost:9090/api/v1/targets > /dev/null 2>&1 && echo "  ✓ Prometheus scraping" || echo "  ✗ Prometheus"
curl -s http://localhost:3000/api/health > /dev/null 2>&1 && echo "  ✓ Grafana healthy" || echo "  ✗ Grafana"

# ----------------------------------------------------------
# Banner
# ----------------------------------------------------------
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅  Master-Pi Demo RUNNING                            ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  📊 GRAFANA DASHBOARD:                                 ║"
echo "║     http://${LOCAL_IP}:3000/d/heliocore-obs              ║"
echo "║     Login: admin / admin                                ║"
echo "║                                                        ║"
echo "║  📡 Telemetry  → http://${LOCAL_IP}:5000/metrics         ║"
echo "║  📋 Nodes      → http://${LOCAL_IP}:5001/node/list       ║"
echo "║  🔍 Prometheus → http://${LOCAL_IP}:9090                  ║"
echo "║                                                        ║"
echo "║  Next: open another terminal on Farm-Pi and run:       ║"
echo "║    bash demo/demo-farm-pi.sh ${LOCAL_IP}                ║"
echo "║                                                        ║"
echo "║  Stop: bash demo/demo-master-pi.sh stop                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Keep alive, tail logs
echo "Tailing logs... (Ctrl+C to stop)"
tail -f "${LOG_DIR}/telemetry.log" "${LOG_DIR}/prometheus.log" 2>/dev/null || wait
