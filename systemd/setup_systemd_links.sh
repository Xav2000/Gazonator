#!/bin/bash

# Supprime les anciens liens (au cas où)
sudo rm -f /etc/systemd/system/mower_*.service

# Crée les nouveaux liens symboliques
sudo ln -s /home/xav2000/mower_ws/systemd/mower_*.service /etc/systemd/system/

# Recharge systemd
sudo systemctl daemon-reload

echo "Liens symboliques recréés et systemd rechargé !"
