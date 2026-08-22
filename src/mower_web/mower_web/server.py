from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import json
import os
import psutil
import subprocess
from threading import Lock

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
data_lock = Lock()

ZONES_FILE = "zones.json"
TASKS_FILE = "tasks.json"
SETTINGS_FILE = "settings.json"

zones = []
tasks = []
settings = {}

def load_data():
    global zones, tasks, settings
    with data_lock:
        try:
            with open(ZONES_FILE, "r") as f:
                zones = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            zones = []
        try:
            with open(TASKS_FILE, "r") as f:
                tasks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            tasks = []
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}

def save_data():
    with data_lock:
        with open(ZONES_FILE, "w") as f:
            json.dump(zones, f, indent=2)
        with open(TASKS_FILE, "w") as f:
            json.dump(tasks, f, indent=2)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)

@app.route("/api/zones", methods=["GET"])
def get_zones():
    return jsonify(zones)

@app.route("/api/zones", methods=["POST"])
def save_zones():
    global zones
    with data_lock:
        zones = request.json
        save_data()
        socketio.emit("zones_updated", {"zones": zones}, broadcast=True)
    return jsonify({"success": True})

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks)

@app.route("/api/tasks", methods=["POST"])
def save_tasks():
    global tasks
    with data_lock:
        tasks = request.json
        save_data()
    return jsonify({"success": True})

@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(settings)

@app.route("/api/settings", methods=["POST"])
def save_settings():
    global settings
    with data_lock:
        settings = request.json
        save_data()
    return jsonify({"success": True})

@app.route("/api/system_status")
def system_status():
    cpu_percent = psutil.cpu_percent(interval=1)
    ram_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage("/").percent
    return jsonify({
        "cpu": cpu_percent,
        "ram": ram_percent,
        "disk": disk_percent
    })

@app.route("/api/ros_nodes")
def ros_nodes():
    try:
        result = subprocess.run(
            ["ros", "node", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        nodes = []
        if result.stdout:
            for line in result.stdout.strip().split("
"):
                if line.strip():
                    nodes.append({
                        "name": line.strip(),
                        "status": "running"
                    })
        return jsonify({"nodes": nodes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ros/restart_node", methods=["POST"])
def restart_ros_node():
    node_name = request.json.get("node_name")
    if not node_name:
        return jsonify({"success": False, "error": "Nom du nœud manquant"}), 400
    try:
        subprocess.run(
            ["ros", "node", "kill", node_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ros_command", methods=["POST"])
def ros_command():
    command = request.json
    try:
        if command.get("type") == "manual_control":
            linear_x = command.get("linear_x", 0)
            angular_z = command.get("angular_z", 0)
            subprocess.run([
                "rostopic", "pub", "/cmd_vel", "geometry_msgs/Twist",
                f"'{linear_x: .2f}, 0, 0, 0, 0, {angular_z: .2f}'"
            ])
        elif command.get("type") == "stop":
            subprocess.run([
                "rostopic", "pub", "/cmd_vel", "geometry_msgs/Twist",
                "'0, 0, 0, 0, 0, 0'"
            ])
        elif command.get("type") == "start_mission":
            zone_ids = command.get("zones", [])
            print(f"Démarrage de la mission avec les zones: {zone_ids}")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@socketio.on("connect")
def handle_connect():
    print("✅ Client connecté")
    socketio.emit("zones_updated", {"zones": zones})

@socketio.on("disconnect")
def handle_disconnect():
    print("❌ Client déconnecté")

@socketio.on("select_zone_for_mission")
def handle_select_zone_for_mission(data):
    zone_id = data.get("zone_id")
    print(f"Zone sélectionnée pour la mission: {zone_id}")
    socketio.emit("mission_updated", {"zone_id": zone_id}, broadcast=True)

@socketio.on("ros_command")
def handle_ros_command(command):
    print(f"Commande ROS reçue: {command}")

if __name__ == "__main__":
    load_data()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)