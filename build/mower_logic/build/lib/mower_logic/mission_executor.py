#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from geometry_msgs.msg import Twist
import json
import math
import os

class MissionExecutor(Node):
    def __init__(self):
        super().__init__('mission_executor')

        # Paramètres & chemins (pour xav2000)
        self.declare_parameter('json_map_path', os.path.expanduser('~/mower_dashboard/data/map_data.json'))
        self.declare_parameter('target_speed', 0.3)  # m/s
        self.declare_parameter('goal_tolerance', 0.4)  # mètres

        self.json_path = self.get_parameter('json_map_path').get_parameter_value().string_value
        self.target_speed = self.get_parameter('target_speed').get_parameter_value().double_value
        self.tolerance = self.get_parameter('goal_tolerance').get_parameter_value().double_value

        # Publishers / Subscribers
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.gps_sub = self.create_subscription(NavSatFix, '/fix', self.gps_callback, 10)

        # État de la mission
        self.current_lat = None
        self.current_lon = None
        self.origin_lat = None
        self.origin_lon = None

        self.waypoints = []
        self.current_target_idx = 0
        self.is_active = False

        self.get_logger().info("Nœud mission_executor initialisé. En attente du signal GPS et du lancement de mission.")

        # Timer de contrôle (10 Hz)
        self.timer = self.create_timer(0.1, self.control_loop)

    def lat_lon_to_meters(self, lat, lon):
        if self.origin_lat is None:
            return 0.0, 0.0

        R = 6371000.0  # Rayon de la Terre en m
        dlat = math.radians(lat - self.origin_lat)
        dlon = math.radians(lon - self.origin_lon)

        x = dlon * R * math.cos(math.radians(self.origin_lat))
        y = dlat * R
        return x, y

    def load_mission_from_json(self):
        if not os.path.exists(self.json_path):
            self.get_logger().error(f"Fichier de carte introuvable : {self.json_path}")
            return False

        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)

            zones = data.get('zones', [])
            if not zones or len(zones[0].get('points', [])) < 3:
                self.get_logger().error("Aucune zone valide avec au moins 3 points trouvée.")
                return False

            raw_points = zones[0]['points']
            self.origin_lat = raw_points[0]['lat']
            self.origin_lon = raw_points[0]['lon']

            self.waypoints = []
            for p in raw_points:
                x, y = self.lat_lon_to_meters(p['lat'], p['lon'])
                self.waypoints.append((x, y))

            self.get_logger().info(f"Mission chargée : {len(self.waypoints)} waypoints calculés.")
            return True

        except Exception as e:
            self.get_logger().error(f"Erreur de lecture du JSON : {e}")
            return False

    def gps_callback(self, msg: NavSatFix):
        if msg.status.status >= 0:
            self.current_lat = msg.latitude
            self.current_lon = msg.longitude

    def control_loop(self):
        if not self.is_active or self.current_lat is None or not self.waypoints:
            return

        curr_x, curr_y = self.lat_lon_to_meters(self.current_lat, self.current_lon)
        target_x, target_y = self.waypoints[self.current_target_idx]

        dx = target_x - curr_x
        dy = target_y - curr_y
        dist = math.hypot(dx, dy)

        if dist < self.tolerance:
            self.get_logger().info(f"Waypoint {self.current_target_idx + 1} atteint !")
            self.current_target_idx += 1
            
            if self.current_target_idx >= len(self.waypoints):
                self.get_logger().info("Mission terminée avec succès !")
                self.stop_robot()
                self.is_active = False
                return

        cmd = Twist()
        cmd.linear.x = min(self.target_speed, 0.5 * dist)
        cmd.angular.z = 0.0

        self.cmd_pub.publish(cmd)

    def stop_robot(self):
        cmd = Twist()
        self.cmd_pub.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = MissionExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.stop_robot()
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
