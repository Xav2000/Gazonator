import os
import json
import psutil
from flask import Flask, jsonify, request, send_from_directory
from mower_web.path_planner import generate_coverage_path

DATA_DIR = os.path.expanduser('~/mower_ws/src/mower_web/data')
ZONES_FILE = os.path.join(DATA_DIR, 'zones.geojson')

app = Flask(__name__, static_folder='static', static_url_path='')

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/zones', methods=['GET'])
def get_zones():
    if not os.path.exists(ZONES_FILE):
        return jsonify({"type": "FeatureCollection", "features": []})
    try:
        with open(ZONES_FILE, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/zones', methods=['POST'])
def save_zones():
    try:
        data = request.json
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ZONES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_path', methods=['POST'])
def api_generate_path():
    data = request.json or {}
    turn_count = int(data.get('turn_count', 2))
    cut_width = float(data.get('cut_width', 0.4))
    overlap = float(data.get('overlap', 0.05))
    angle = data.get('angle', 0)
    ref_edge = data.get('ref_edge', None)

    geojson = generate_coverage_path(
        turn_count=turn_count,
        cut_width=cut_width,
        overlap=overlap,
        angle_deg=angle,
        ref_edge=ref_edge
    )
    return jsonify(geojson)

@app.route('/api/system', methods=['GET'])
def get_system_metrics():
    try:
        cpu_usage = psutil.cpu_percent(interval=None)
        
        # Température CPU sur Raspberry Pi
        cpu_temp = 0.0
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                cpu_temp = round(float(f.read().strip()) / 1000.0, 1)
        except Exception:
            pass

        ram = psutil.virtual_memory()
        ram_usage_mb = round((ram.total - ram.available) / (1024 * 1024), 1)
        ram_total_mb = round(ram.total / (1024 * 1024), 1)

        disk = psutil.disk_usage('/')
        disk_free_gb = round(disk.free / (1024 * 1024 * 1024), 1)

        return jsonify({
            "cpu_usage": cpu_usage,
            "cpu_temp": cpu_temp,
            "ram_usage_mb": ram_usage_mb,
            "ram_total_mb": ram_total_mb,
            "disk_free_gb": disk_free_gb
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
