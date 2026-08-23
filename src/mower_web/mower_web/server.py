#!/usr/bin/env python3
import os
import sys
import json
import psutil
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.append(str(Path(__file__).parent.resolve()))
from path_generator import PathGenerator

app = Flask(__name__, static_folder='static')
CORS(app)

STORAGE_DIR = os.path.expanduser('~/mower_ws/src/mower_web/mower_web/storage')
os.makedirs(STORAGE_DIR, exist_ok=True)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('static', path)

@app.route('/api/system', methods=['GET'])
def get_system_status():
    temp = 0.0
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
    except:
        pass
    disk = psutil.disk_usage('/')
    memory = psutil.virtual_memory()
    return jsonify({
        'cpu_usage': psutil.cpu_percent(interval=None),
        'cpu_temp': round(temp, 1),
        'ram_usage_mb': round(memory.used / (1024 * 1024), 1),
        'ram_total_mb': round(memory.total / (1024 * 1024), 1),
        'disk_free_gb': round(disk.free / (1024**3), 1)
    })

@app.route('/api/generate_path', methods=['POST'])
def generate_path():
    data = request.json
    try:
        generator = PathGenerator(
            zone_latlng=data['polygon'],
            exclusions_latlng=data.get('exclusions', []),
            num_tours=data['tours'],
            width=data['largeur']
        )
        result = generator.generate()
        return jsonify({'status': 'success', 'waypoints': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    tasks = []
    for f in os.listdir(STORAGE_DIR):
        if f.endswith('.json'):
            with open(os.path.join(STORAGE_DIR, f), 'r') as file:
                tasks.append(json.load(file))
    return jsonify(tasks)

@app.route('/api/tasks/<task_id>', methods=['POST'])
def save_task(task_id):
    data = request.json
    data['id'] = task_id
    file_path = os.path.join(STORAGE_DIR, f"{task_id}.json")
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({'status': 'success', 'task_id': task_id})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    file_path = os.path.join(STORAGE_DIR, f"{task_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'status': 'deleted'})
    return jsonify({'status': 'not_found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
