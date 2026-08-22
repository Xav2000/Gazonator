#!/bin/bash
source /opt/ros/humble/setup.bash
source /home/xav2000/mower_ws/install/setup.bash 2>/dev/null || true

# Ajoute le dossier src au chemin de recherche Python
export PYTHONPATH=/home/xav2000/mower_ws/src/mower_web:$PYTHONPATH

# Lancement de rosbridge en arrière-plan s'il n'est pas déjà lancé
pgrep -f rosbridge_websocket > /dev/null || ros2 launch rosbridge_server rosbridge_websocket_launch.xml &

# Attente de 1 seconde pour rosbridge
sleep 1

# Lancement du serveur Flask
python3 /home/xav2000/mower_ws/src/mower_web/mower_web/server.py
