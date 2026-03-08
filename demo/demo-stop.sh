#!/bin/bash
# ============================================================
# HelioCore OS — Stop Demo Services
# Run: bash demo/demo-stop.sh
# ============================================================

echo "Stopping HelioCore demo services..."

pkill -f "telemetry_server.py" 2>/dev/null && echo "  ✓ Telemetry server stopped" || echo "  - Telemetry server not running"
pkill -f "node_registry.py" 2>/dev/null && echo "  ✓ Node registry stopped" || echo "  - Node registry not running"
pkill -f "demo_simulator.py" 2>/dev/null && echo "  ✓ Simulator stopped" || echo "  - Simulator not running"
pkill -f "heliocore_os.py" 2>/dev/null && echo "  ✓ CLI dashboard stopped" || echo "  - CLI dashboard not running"

rm -f /tmp/heliocore/pids/*.pid 2>/dev/null

echo ""
echo "All demo services stopped."
