#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
import serial
import math
import time

class MotorDriverNode(Node):
    def __init__(self):
        super().__init__('motor_driver_node')

        # Paramètres série et cinématique
        self.declare_parameter('port', '/dev/serial/by-id/usb-Arduino_LLC_Arduino_Nano_Every_D7D5242451544E5450202020FF061D32-if00')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('wheel_radius', 0.13)      # 260 mm / 2
        self.declare_parameter('wheel_separation', 0.60)  # 60 cm
        self.declare_parameter('steps_per_rev', 8000.0)    # 1600 pas * 5 (réducteur)

        port = self.get_parameter('port').get_parameter_value().string_value
        baudrate = self.get_parameter('baudrate').get_parameter_value().integer_value
        self.R = self.get_parameter('wheel_radius').get_parameter_value().double_value
        self.L = self.get_parameter('wheel_separation').get_parameter_value().double_value
        self.steps_per_rev = self.get_parameter('steps_per_rev').get_parameter_value().double_value

        # Connexion Série
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.1)
            self.get_logger().info(f"Connecté à l'Arduino sur {port}")
        except Exception as e:
            self.get_logger().error(f"Impossible d'ouvrir le port série {port}: {e}")

        # Variables d'état odométrique (x, y, theta)
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.last_steps_L = None
        self.last_steps_R = None
        self.last_time = self.get_clock().now()

        # Publishers / Subscribers / TF
        self.sub_cmd_vel = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.pub_odom = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Timer de lecture de la liaison série (20 Hz)
        self.timer = self.create_timer(0.05, self.read_serial)

    def cmd_vel_callback(self, msg):
        v = msg.linear.x
        w = msg.angular.z

        # Calcul des vitesses angulaires des roues (rad/s)
        rad_s_L = (v - (w * self.L / 2.0)) / self.R
        rad_s_R = (v + (w * self.L / 2.0)) / self.R

        # Formatage du message pour l'Arduino: "V:rad_L,rad_R\n"
        cmd_str = f"V:{rad_s_L:.2f},{rad_s_R:.2f}\n"
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.write(cmd_str.encode('utf-8'))

    def read_serial(self):
        if not hasattr(self, 'ser') or not self.ser.is_open:
            return

        while self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                if line.startswith("O:"):
                    # Format reçu: "O:stepsL,stepsR"
                    parts = line[2:].split(',')
                    steps_L = int(parts[0])
                    steps_R = int(parts[1])

                    self.update_odometry(steps_L, steps_R)
            except Exception as e:
                self.get_logger().warn(f"Erreur de lecture série: {e}")

    def update_odometry(self, steps_L, steps_R):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9

        if self.last_steps_L is None:
            self.last_steps_L = steps_L
            self.last_steps_R = steps_R
            self.last_time = current_time
            return

        # Calcul des deltas en mètres
        delta_steps_L = steps_L - self.last_steps_L
        delta_steps_R = steps_R - self.last_steps_R

        self.last_steps_L = steps_L
        self.last_steps_R = steps_R

        dist_L = (delta_steps_L / self.steps_per_rev) * (2.0 * math.pi * self.R)
        dist_R = (delta_steps_R / self.steps_per_rev) * (2.0 * math.pi * self.R)

        d_center = (dist_L + dist_R) / 2.0
        d_theta = (dist_R - dist_L) / self.L

        # Intégration de la position
        if d_center != 0:
            self.x += d_center * math.cos(self.theta + d_theta / 2.0)
            self.y += d_center * math.sin(self.theta + d_theta / 2.0)
        self.theta += d_theta

        # Quaternion pour ROS
        qz = math.sin(self.theta / 2.0)
        qw = math.cos(self.theta / 2.0)

        # 1. Publication de la TF odom -> base_link
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)

        # 2. Publication du Topic /odom
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw

        if dt > 0:
            odom.twist.twist.linear.x = d_center / dt
            odom.twist.twist.angular.z = d_theta / dt

        self.pub_odom.publish(odom)
        self.last_time = current_time

def main(args=None):
    rclpy.init(args=args)
    node = MotorDriverNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
