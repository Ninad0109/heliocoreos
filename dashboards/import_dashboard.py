#!/usr/bin/env python3
"""Import HelioCore dashboard into local Grafana."""
import json, requests

GRAFANA_URL = "http://localhost:3000"
AUTH = ("admin", "admin")

# Build a v1-format dashboard for local Grafana + Prometheus
dashboard = {
    "title": "HelioCore OS — Solar Farm Observability",
    "uid": "heliocore-obs",
    "tags": ["heliocore", "solar"],
    "timezone": "browser",
    "refresh": "2s",
    "time": {"from": "now-15m", "to": "now"},
    "panels": []
}

pid = 0
def panel(title, ptype, x, y, w, h, targets=None, field_config=None, options=None):
    global pid
    pid += 1
    p = {"id": pid, "title": title, "type": ptype, "gridPos": {"x": x, "y": y, "w": w, "h": h}}
    if targets:
        p["targets"] = targets
    if field_config:
        p["fieldConfig"] = field_config
    if options:
        p["options"] = options
    return p

def section(title, y):
    return panel(title, "text", 0, y, 24, 2, options={
        "mode": "html",
        "content": f'<div style="display:flex;align-items:center;height:100%;padding:0 8px;">'
                   f'<div style="width:3px;height:16px;background:#F46800;margin-right:10px;border-radius:2px;"></div>'
                   f'<span style="font-size:12px;font-weight:700;letter-spacing:3px;color:#9FA7B3;text-transform:uppercase;">{title}</span></div>'
    })

def stat_panel(title, expr, x, y, w, h, mappings=None, thresholds=None, color_mode="background_solid"):
    fc = {"defaults": {"color": {"mode": "thresholds"}}}
    if mappings:
        fc["defaults"]["mappings"] = [{"type": "value", "options": mappings}]
    if thresholds:
        fc["defaults"]["thresholds"] = {"mode": "absolute", "steps": thresholds}
    return panel(title, "stat", x, y, w, h,
                 targets=[{"expr": expr, "legendFormat": title, "refId": "A", "instant": True}],
                 field_config=fc,
                 options={"colorMode": color_mode, "graphMode": "none", "justifyMode": "center", "textMode": "value_and_name"})

def gauge_panel(title, expr, x, y, w, h, unit="degree", mn=0, mx=90, steps=None):
    return panel(title, "gauge", x, y, w, h,
                 targets=[{"expr": expr, "legendFormat": title, "refId": "A", "instant": True}],
                 field_config={"defaults": {
                     "unit": unit, "min": mn, "max": mx,
                     "thresholds": {"mode": "absolute", "steps": steps or []},
                     "color": {"mode": "thresholds"}
                 }},
                 options={"showThresholdLabels": True, "showThresholdMarkers": True})

def ts_panel(title, expr, x, y, w, h, unit="", color="orange", mn=0, mx=None):
    fc = {"defaults": {
        "color": {"mode": "fixed", "fixedColor": color},
        "custom": {"drawStyle": "line", "fillOpacity": 15, "gradientMode": "opacity",
                   "lineInterpolation": "smooth", "lineWidth": 2, "showPoints": "never", "spanNulls": True}
    }}
    if unit: fc["defaults"]["unit"] = unit
    if mn is not None: fc["defaults"]["min"] = mn
    if mx is not None: fc["defaults"]["max"] = mx
    return panel(title, "timeseries", x, y, w, h,
                 targets=[{"expr": expr, "legendFormat": title, "refId": "A"}],
                 field_config=fc)

P = dashboard["panels"]

# === SYSTEM STATUS ===
P.append(section("SYSTEM STATUS", 0))
P.append(stat_panel("Farm Node", "farm_online", 0, 2, 6, 5,
    {"0": {"text": "OFFLINE", "color": "dark-red"}, "1": {"text": "ONLINE", "color": "green"}},
    [{"value": None, "color": "dark-red"}, {"value": 1, "color": "green"}]))
P.append(stat_panel("Petal State", "petal_state", 6, 2, 6, 5,
    {"0": {"text": "CLOSED", "color": "blue"}, "1": {"text": "OPEN", "color": "green"}},
    [{"value": None, "color": "blue"}, {"value": 1, "color": "green"}]))
P.append(stat_panel("Tracking", "tracking_active", 12, 2, 6, 5,
    {"0": {"text": "INACTIVE", "color": "gray"}, "1": {"text": "TRACKING", "color": "green"}},
    [{"value": None, "color": "gray"}, {"value": 1, "color": "green"}]))
P.append(stat_panel("Service Health", "heliocore_service_health", 18, 2, 6, 5,
    {"0": {"text": "DOWN", "color": "dark-red"}, "1": {"text": "UP", "color": "green"}},
    [{"value": None, "color": "dark-red"}, {"value": 1, "color": "green"}]))
P.append(ts_panel("CPU Usage", "cpu_usage", 0, 7, 12, 7, unit="percent", color="orange", mn=0, mx=100))
P.append(ts_panel("Memory Usage", "memory_usage", 12, 7, 12, 7, unit="percent", color="purple", mn=0, mx=100))

# === PANEL ORIENTATION ===
P.append(section("PANEL ORIENTATION", 14))
P.append(gauge_panel("Base Angle", "base_angle", 0, 16, 12, 8, mn=-160, mx=160,
    steps=[{"value": None, "color": "super-light-blue"}, {"value": -80, "color": "blue"},
           {"value": -10, "color": "green"}, {"value": 10, "color": "blue"}, {"value": 80, "color": "super-light-blue"}]))
P.append(gauge_panel("Tilt Angle", "tilt_angle", 12, 16, 12, 8, mn=0, mx=90,
    steps=[{"value": None, "color": "green"}, {"value": 60, "color": "yellow"},
           {"value": 75, "color": "orange"}, {"value": 85, "color": "dark-red"}]))
P.append(gauge_panel("Alignment Error", "alignment_error", 0, 24, 12, 7, mn=0, mx=90,
    steps=[{"value": None, "color": "green"}, {"value": 5, "color": "yellow"},
           {"value": 20, "color": "orange"}, {"value": 45, "color": "dark-red"}]))
P.append(stat_panel("Tracking Direction", "tracking_direction", 12, 24, 12, 7,
    {"0": {"text": "IDLE", "color": "gray"}, "1": {"text": "▶ EAST", "color": "yellow"},
     "2": {"text": "◀ WEST", "color": "orange"}, "3": {"text": "▲ UP", "color": "super-light-blue"},
     "4": {"text": "▼ DOWN", "color": "blue"}, "5": {"text": "◎ ZENITH", "color": "green"}},
    [{"value": None, "color": "gray"}, {"value": 1, "color": "green"}]))
P.append(stat_panel("Solar Intensity Avg", "light_intensity_avg", 0, 31, 24, 5,
    None, [{"value": None, "color": "blue"}, {"value": 400, "color": "yellow"}, {"value": 750, "color": "super-light-orange"}],
    color_mode="value"))

# === MOTOR SYSTEM ===
P.append(section("MOTOR SYSTEM", 36))
P.append(stat_panel("Motor Base", "motor_base_state", 0, 38, 8, 6,
    {"0": {"text": "IDLE", "color": "blue"}, "1": {"text": "RUNNING", "color": "green"},
     "2": {"text": "STALLED", "color": "orange"}, "3": {"text": "FAULT", "color": "dark-red"}},
    [{"value": None, "color": "blue"}, {"value": 1, "color": "green"}, {"value": 2, "color": "orange"}, {"value": 3, "color": "dark-red"}]))
P.append(stat_panel("Motor Tilt", "motor_tilt_state", 8, 38, 8, 6,
    {"0": {"text": "IDLE", "color": "blue"}, "1": {"text": "RUNNING", "color": "green"},
     "2": {"text": "STALLED", "color": "orange"}, "3": {"text": "FAULT", "color": "dark-red"}},
    [{"value": None, "color": "blue"}, {"value": 1, "color": "green"}, {"value": 2, "color": "orange"}, {"value": 3, "color": "dark-red"}]))
P.append(gauge_panel("Motor Temperature", "motor_temperature", 16, 38, 8, 6, unit="celsius", mn=0, mx=100,
    steps=[{"value": None, "color": "green"}, {"value": 50, "color": "yellow"},
           {"value": 70, "color": "orange"}, {"value": 85, "color": "dark-red"}]))

# === SENSOR TELEMETRY ===
P.append(section("SENSOR TELEMETRY", 44))
ldr = panel("LDR Sensors", "stat", 0, 46, 16, 6,
    targets=[
        {"expr": "ldr_left", "legendFormat": "Left", "refId": "A", "instant": True},
        {"expr": "ldr_right", "legendFormat": "Right", "refId": "B", "instant": True},
        {"expr": "ldr_top", "legendFormat": "Top", "refId": "C", "instant": True},
        {"expr": "ldr_bottom", "legendFormat": "Bottom", "refId": "D", "instant": True},
    ],
    field_config={"defaults": {"color": {"mode": "palette-classic"}}},
    options={"colorMode": "value", "graphMode": "none", "justifyMode": "center",
             "textMode": "value_and_name", "orientation": "horizontal"})
P.append(ldr)
P.append(stat_panel("Rain Sensor", "rain_sensor", 16, 46, 8, 6,
    {"0": {"text": "DRY", "color": "green"}, "1": {"text": "RAIN DETECTED", "color": "dark-blue"}},
    [{"value": None, "color": "green"}, {"value": 1, "color": "dark-blue"}]))

# === NODE CONNECTIVITY ===
P.append(section("NODE CONNECTIVITY", 52))
P.append(ts_panel("Farm Node Latency", "farm_node_latency", 0, 54, 24, 7, unit="ms", color="cyan", mn=0))


# Import into Grafana
payload = {"dashboard": dashboard, "overwrite": True}

r = requests.post(f"{GRAFANA_URL}/api/dashboards/db", json=payload, auth=AUTH, timeout=10)
if r.ok:
    data = r.json()
    print(f"✓ Dashboard imported successfully!")
    print(f"  URL: {GRAFANA_URL}{data.get('url', '/d/heliocore-obs')}")
    print(f"  UID: {data.get('uid', 'heliocore-obs')}")
else:
    print(f"✗ Failed: {r.status_code} {r.text}")
