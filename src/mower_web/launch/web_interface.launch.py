import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():
    server_script = os.path.expanduser('~/mower_ws/src/mower_web/mower_web/server.py')

    return LaunchDescription([
        # 1. WebSocket Rosbridge (Port 9090)
        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge_websocket',
            output='screen',
            parameters=[{'port': 9090}]
        ),
        # 2. Serveur Web Flask (Port 5000)
        ExecuteProcess(
            cmd=['python3', server_script],
            output='screen'
        )
    ])
