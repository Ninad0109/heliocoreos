#!/bin/bash
# ============================================================
# HelioCore OS — Demo Farm-Pi
# Runs: simulator + HelioCore OS CLI terminal with live logs
#
# Usage:
#   bash demo/demo-farm-pi.sh [master-ip]
#
# Examples:
#   bash demo/demo-farm-pi.sh              # localhost (testing)
#   bash demo/demo-farm-pi.sh 192.168.1.100  # real Master-Pi
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELIO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${HELIO_DIR}/.venv-farm"
MASTER_IP="${1:-localhost}"
MASTER_URL="http://${MASTER_IP}:5000"
LOG_DIR="/tmp/heliocore/logs"
PID_DIR="/tmp/heliocore/pids"

# ----------------------------------------------------------
# Stop command
# ----------------------------------------------------------
if [ "$1" = "stop" ]; then
    echo "Stopping Farm-Pi demo..."
    [ -f ${PID_DIR}/simulator.pid ] && kill $(cat ${PID_DIR}/simulator.pid) 2>/dev/null && echo "  ✓ Simulator stopped"
    rm -f ${PID_DIR}/simulator.pid
    echo "Done."
    exit 0
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     HelioCore OS — Farm-Pi Demo                        ║"
echo "║     Simulator + CLI Terminal + Live Logs                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# ----------------------------------------------------------
# 1. Virtual environment
# ----------------------------------------------------------
echo "[1/5] Setting up Python virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
    echo "  ✓ Created: ${VENV_DIR}"
else
    echo "  ✓ Already exists"
fi
source "${VENV_DIR}/bin/activate"
echo "  ✓ Activated"

# ----------------------------------------------------------
# 2. Install dependencies
# ----------------------------------------------------------
echo "[2/5] Installing packages..."
pip install --quiet --upgrade pip
pip install --quiet requests==2.31.0 psutil==5.9.0 prompt-toolkit==3.0.36
echo "  ✓ Dependencies installed"

# ----------------------------------------------------------
# 3. Create directories
# ----------------------------------------------------------
echo "[3/5] Setting up directories..."
mkdir -p "${LOG_DIR}" "${PID_DIR}"
echo "  ✓ Ready"

# ----------------------------------------------------------
# 4. Test connection to Master-Pi
# ----------------------------------------------------------
echo "[4/5] Connecting to Master-Pi at ${MASTER_URL}..."
RETRIES=0
MAX_RETRIES=10
until curl -s "${MASTER_URL}/status" > /dev/null 2>&1; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo "  ✗ Cannot reach Master-Pi at ${MASTER_URL}"
        echo ""
        echo "  Make sure demo-master-pi.sh is running first!"
        echo "  Usage: bash demo/demo-farm-pi.sh [master-ip]"
        exit 1
    fi
    echo "  Waiting for Master-Pi... (${RETRIES}/${MAX_RETRIES})"
    sleep 2
done
echo "  ✓ Connected to Master-Pi"

# Register as a node
HOSTNAME=$(hostname)
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
curl -s -X POST "http://${MASTER_IP}:5001/node/register" \
    -H "Content-Type: application/json" \
    -d "{\"node_id\": \"${HOSTNAME}\", \"ip\": \"${LOCAL_IP}\", \"hostname\": \"${HOSTNAME}\"}" \
    > /dev/null 2>&1 && echo "  ✓ Registered as '${HOSTNAME}'" || echo "  ⚠ Registry unavailable (non-critical)"

# ----------------------------------------------------------
# 5. Start simulator in background, then launch CLI
# ----------------------------------------------------------
echo "[5/5] Starting simulator & CLI..."

# Start simulator as background process
python3 "${HELIO_DIR}/demo/demo_simulator.py" \
    --master "${MASTER_URL}" \
    --interval 1.0 \
    --speed 0.005 \
    > "${LOG_DIR}/simulator.log" 2>&1 &
SIM_PID=$!
echo "${SIM_PID}" > "${PID_DIR}/simulator.pid"
sleep 2

if kill -0 $SIM_PID 2>/dev/null; then
    echo "  ✓ Simulator running in background (PID ${SIM_PID})"
    echo "    Sending 21 metrics/tick to ${MASTER_URL}"
else
    echo "  ✗ Simulator failed to start"
    cat "${LOG_DIR}/simulator.log"
    exit 1
fi

# ----------------------------------------------------------
# CLI Terminal
# ----------------------------------------------------------
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅  Farm-Pi Demo RUNNING                              ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  Simulator → sending data to ${MASTER_IP}:5000          ║"
echo "║  Logs      → ${LOG_DIR}/simulator.log                  ║"
echo "║                                                        ║"
echo "║  Launching HelioCore OS terminal...                    ║"
echo "║  Type 'help' for available commands                    ║"
echo "║  Type 'logs' to view live simulator logs               ║"
echo "║  Type 'exit' to stop                                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Display HelioCore OS boot banner
echo ""
echo "  ██╗  ██╗███████╗██╗     ██╗ ██████╗  ██████╗ ██████╗ ██████╗ ███████╗"
echo "  ██║  ██║██╔════╝██║     ██║██╔═══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝"
echo "  ███████║█████╗  ██║     ██║██║   ██║██║     ██║   ██║██████╔╝█████╗  "
echo "  ██╔══██║██╔══╝  ██║     ██║██║   ██║██║     ██║   ██║██╔══██╗██╔══╝  "
echo "  ██║  ██║███████╗███████╗██║╚██████╔╝╚██████╗╚██████╔╝██║  ██║███████╗"
echo "  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
echo ""
echo "  HelioCore OS v1.0 — Solar Tracking System"
echo "  Node: ${HOSTNAME} | Master: ${MASTER_IP}"
echo ""

# Launch interactive loop
export PYTHONPATH="${HELIO_DIR}:${PYTHONPATH}"

while true; do
    read -p "heliocore@${HOSTNAME}> " CMD ARGS

    case "$CMD" in
        help)
            echo ""
            echo "  Available commands:"
            echo "  ─────────────────────────────────────────────────"
            echo "  status      — Show simulator status and metrics"
            echo "  logs        — Tail simulator log (Ctrl+C to exit)"
            echo "  metrics     — Show current /metrics from Master"
            echo "  nodes       — List registered nodes"
            echo "  health      — System health check"
            echo "  top         — Show CPU/memory usage"
            echo "  clear       — Clear screen"
            echo "  restart     — Restart the simulator"
            echo "  exit        — Stop simulator and exit"
            echo ""
            ;;
        status)
            echo ""
            if kill -0 $(cat "${PID_DIR}/simulator.pid" 2>/dev/null) 2>/dev/null; then
                echo "  🟢 Simulator: RUNNING (PID $(cat ${PID_DIR}/simulator.pid))"
            else
                echo "  🔴 Simulator: STOPPED"
            fi
            echo "  📡 Master:    ${MASTER_URL}"
            echo ""
            # Fetch current status from master
            STATUS=$(curl -s "${MASTER_URL}/status" 2>/dev/null)
            if [ -n "$STATUS" ]; then
                echo "  Current telemetry:"
                echo "$STATUS" | python3 -m json.tool 2>/dev/null | head -30
            fi
            echo ""
            ;;
        logs)
            echo "  Tailing simulator log... (Ctrl+C to return)"
            tail -f "${LOG_DIR}/simulator.log" 2>/dev/null || echo "  No log file found"
            ;;
        metrics)
            echo ""
            curl -s "${MASTER_URL}/metrics" 2>/dev/null | while read line; do
                echo "  $line"
            done
            echo ""
            ;;
        nodes)
            echo ""
            curl -s "http://${MASTER_IP}:5001/node/list" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  Registry unavailable"
            echo ""
            ;;
        health)
            echo ""
            echo "  System Health:"
            echo "  ─────────────────────────────────────────────────"
            if kill -0 $(cat "${PID_DIR}/simulator.pid" 2>/dev/null) 2>/dev/null; then
                echo "  Simulator:    ✅ Running"
            else
                echo "  Simulator:    ❌ Stopped"
            fi
            curl -s "${MASTER_URL}/status" > /dev/null 2>&1 && echo "  Master Link:  ✅ Connected" || echo "  Master Link:  ❌ Disconnected"
            curl -s "http://${MASTER_IP}:5001/node/list" > /dev/null 2>&1 && echo "  Registry:     ✅ Available" || echo "  Registry:     ⚠  Unavailable"
            echo ""
            if command -v python3 -c "import psutil" 2>/dev/null; then
                python3 -c "import psutil; print(f'  CPU:          {psutil.cpu_percent()}%'); print(f'  Memory:       {psutil.virtual_memory().percent}%'); print(f'  Disk:         {psutil.disk_usage(\"/\").percent}%')" 2>/dev/null || true
            fi
            echo ""
            ;;
        top)
            python3 -c "
import psutil, time, os
try:
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        print('  HelioCore OS — System Monitor')
        print('  ─────────────────────────────')
        print(f'  CPU:    {psutil.cpu_percent():5.1f}%')
        print(f'  Memory: {psutil.virtual_memory().percent:5.1f}%')
        print(f'  Disk:   {psutil.disk_usage(\"/\").percent:5.1f}%')
        print(f'  Procs:  {len(psutil.pids())}')
        print()
        print('  Press Ctrl+C to return')
        time.sleep(1)
except KeyboardInterrupt:
    pass
" 2>/dev/null || echo "  psutil not available"
            ;;
        clear)
            clear
            ;;
        restart)
            echo "  Restarting simulator..."
            [ -f ${PID_DIR}/simulator.pid ] && kill $(cat ${PID_DIR}/simulator.pid) 2>/dev/null
            sleep 1
            python3 "${HELIO_DIR}/demo/demo_simulator.py" \
                --master "${MASTER_URL}" \
                --interval 1.0 \
                --speed 0.005 \
                > "${LOG_DIR}/simulator.log" 2>&1 &
            echo $! > "${PID_DIR}/simulator.pid"
            sleep 2
            echo "  ✓ Simulator restarted (PID $(cat ${PID_DIR}/simulator.pid))"
            ;;
        exit|quit)
            echo "  Stopping simulator..."
            [ -f ${PID_DIR}/simulator.pid ] && kill $(cat ${PID_DIR}/simulator.pid) 2>/dev/null
            rm -f ${PID_DIR}/simulator.pid
            echo "  HelioCore OS shutting down. Goodbye!"
            exit 0
            ;;
        "")
            ;;
        *)
            echo "  Unknown command: ${CMD}. Type 'help' for available commands."
            ;;
    esac
done
