#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from robot_localization.srv import FromLL
from geographic_msgs.msg import GeoPoint
import math

class GPSWaypointFollower(Node):
    def __init__(self):
        super().__init__('gps_waypoint_follower')

        # Client pour le service de conversion GPS -> Map
        self.from_ll_client = self.create_client(FromLL, '/fromLL')
        while not self.from_ll_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().info('En attente du service /fromLL (navsat_transform)...')

        # Client d'action Nav2
        self.nav_to_pose_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Exemples de coordonnées GPS (À remplacer par les coins de ta pelouse)
        self.waypoints_gps = [
            (47.065123, 4.887123),  # Point 1
            (47.065200, 4.887200),  # Point 2
            (47.065150, 4.887300),  # Point 3
        ]
        self.current_waypoint_index = 0

    def convert_gps_to_pose(self, lat, lon):
        req = FromLL.Request()
        req.ll_point = GeoPoint(latitude=lat, longitude=lon, altitude=0.0)
        
        future = self.from_ll_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None:
            return future.result().map_point
        else:
            self.get_logger().error('Échec de la conversion GPS vers Map')
            return None

    def send_next_waypoint(self):
        if self.current_waypoint_index >= len(self.waypoints_gps):
            self.get_logger().info('Mission terminée ! Tous les points ont été atteints.')
            return

        lat, lon = self.waypoints_gps[self.current_waypoint_index]
        self.get_logger().info(f'Envoi du point {self.current_waypoint_index + 1}/{len(self.waypoints_gps)}: Lat={lat}, Lon={lon}')

        map_point = self.convert_gps_to_pose(lat, lon)
        if map_point is None:
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position = map_point
        goal_msg.pose.pose.orientation.w = 1.0  # Orientation neutre

        self.nav_to_pose_client.wait_for_server()
        self.send_goal_future = self.nav_to_pose_client.send_goal_async(goal_msg)
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Objectif refusé par Nav2')
            return

        self.get_logger().info('Objectif accepté. Tondeuse en route...')
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        self.get_logger().info('Point atteint avec succès !')
        self.current_waypoint_index += 1
        self.send_next_waypoint()

def main(args=None):
    rclpy.init(args=args)
    follower = GPSWaypointFollower()
    follower.send_next_waypoint()
    rclpy.spin(follower)
    follower.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
