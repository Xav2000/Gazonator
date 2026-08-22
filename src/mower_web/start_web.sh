#!/bin/bash

# Obtenir le repertoire du script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
WS_DIR="$(dirname "$SCRIPT_DIR")"

# Source ROS 2
source /opt/ros/humble/setup.bash
source "$WS_DIR/install/setup.bash" 2>/dev/null || source "$WS_DIR/install/local_setup.bash" 2>/dev/null || true

# Ajoute le dossier src au chemin de recherche Python
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Lancement de rosbridge en arriere-plan s'il n'est pas deja lance
pgrep -f rosbridge_websocket > /dev/null || ros2 launch rosbridge_server rosbridge_websocket_launch.xml &

# Attente de 1 seconde pour rosbridge
sleep 1

# Lancement du serveur Flask
python3 "$SCRIPT_DIR/mower_web/server.py"