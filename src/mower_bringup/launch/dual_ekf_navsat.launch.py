import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_mower_bringup = get_package_share_directory('mower_bringup')
    config_file = os.path.join(pkg_mower_bringup, 'config', 'ekf_gps.yaml')

    return LaunchDescription([
        # 1. EKF Local (odom -> base_link)
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_local',
            output='screen',
            parameters=[config_file],
            remappings=[('odometry/filtered', 'odom/local')]
        ),

        # 2. Convertisseur GPS (/fix -> /odometry/gps)
        Node(
            package='robot_localization',
            executable='navsat_transform_node',
            name='navsat_transform_node',
            output='screen',
            parameters=[config_file],
            remappings=[
                ('gps/fix', '/fix'),
                ('odometry/filtered', 'odom/global')
            ]
        ),

        # 3. EKF Global (map -> odom)
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_global',
            output='screen',
            parameters=[config_file],
            remappings=[('odometry/filtered', 'odom/global')]
        )
    ])
