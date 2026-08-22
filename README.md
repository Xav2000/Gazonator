# Gazonator - Tondeuse Autonome ROS 2

## Description
Projet de tondeuse autonome avec navigation GPS RTK, fusion de capteurs (EKF) et planification de mission.

## Prerequis

### Systeme
- Ubuntu 22.04
- Python 3.10+
- Git

### ROS 2
- ROS 2 Humble Hawksbill
- Packages ROS requis:
  sudo apt install ros-humble-ros-base ros-humble-robot-localization ros-humble-ublox-dgnss ros-humble-rosbridge-server ros-humble-nav2-msgs ros-humble-geographic-msgs

### Materiel
- Arduino Nano Every (ou compatible) pour le controle des moteurs
- Recepteur GPS RTK (ex: ZED-F9P)
- Capteurs d odometrie (encodeurs)

## Installation

### 1. Cloner le depot
mkdir -p ~/mower_ws/src
cd ~/mower_ws/src
git clone https://github.com/Xav2000/Gazonator.git
cd ~/mower_ws

### 2. Installer les dependances
rosdep install --from-paths src --ignore-src -r

### 3. Configurer les dependances Python
pip install pyserial flask

### 4. Builder le workspace
colcon build

### 5. Source le workspace
source install/setup.bash

## Lancement

### Lancer le GPS RTK avec correction NTRIP
ros2 launch mower_bringup gps_rtk.launch.py device:=/dev/ttyYOUR_GPS_PORT

### Lancer la navigation (EKF + GPS)
ros2 launch mower_bringup dual_ekf_navsat.launch.py

### Lancer le controleur moteur
ros2 run mower_hardware motor_driver_node

### Lancer l interface web
cd ~/mower_ws/src/mower_web
./start_web.sh

L interface web sera accessible a l adresse: http://localhost:5000

## Structure du projet

Gazonator/
  src/
    mower_bringup/      # Lancement et navigation (EKF, GPS)
      config/         # Fichiers de configuration
      launch/         # Fichiers de lancement
      mower_bringup/  # Scripts Python
    mower_hardware/     # Interface materielle
      config/         # Configuration NTRIP, etc.
      mower_hardware/ # Noeuds ROS (controle moteurs)
    mower_web/          # Interface web
      mower_web/      # Serveur Flask
      start_web.sh    # Script de lancement
  .gitignore              # Fichiers exclus du versionnage
  README.md               # Ce fichier

## Configuration

### Configuration NTRIP
Editez src/mower_hardware/config/centipede_params.yaml pour configurer votre station NTRIP locale.
Pour les identifiants, utilisez des variables d environnement ou un fichier local non versionne.

### Configuration de la mission
- tasks.json: Liste des taches de tonte
- mission_plan.json: Plan de mission (waypoints)
- zones.json: Zones d inclusion/exclusion
- settings.json: Parametres de la tondeuse

> These fichiers contiennent des donnees specifiques a votre environnement.
> Ne les versionnez pas dans un depot public!

## Licence
Apache License 2.0

## Contribution
Les contributions sont les bienvenues! Ouvrez une issue ou une pull request.

## Contact
- Mainteneur: Xavier Rossignol
- Email: xavier.rossignol@free.fr
