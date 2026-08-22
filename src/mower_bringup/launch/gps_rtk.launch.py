import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Chemins vers les paquets
    mower_hardware_dir = get_package_share_directory('mower_hardware')
    ublox_dgnss_dir = get_package_share_directory('ublox_dgnss')

    # Arguments modifiables lors du lancement
    device_arg = DeclareLaunchArgument(
        'device',
        default_value='/dev/tty_zedf9p',
        description='Port série du ZED-F9P'
    )

    ntrip_config_arg = DeclareLaunchArgument(
        'ntrip_config',
        default_value=os.path.join(mower_hardware_dir, 'config', 'centipede_params.yaml'),
        description='Chemin du fichier de configuration NTRIP Centipede'
    )

    # 1. Inclure le fichier de lancement standard u-blox GNSS + NavSatFix HP
    ublox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ublox_dgnss_dir, 'launch', 'ublox_rover_hpposllh_navsatfix.launch.py')
        ),
        launch_arguments={
            'device': LaunchConfiguration('device')
        }.items()
    )

    # 2. Nœud Client NTRIP pour Centipede
    ntrip_node = Node(
        package='ntrip_client',
        executable='ntrip_ros.py',
        name='ntrip_client',
        output='screen',
        parameters=[LaunchConfiguration('ntrip_config')],
        remappings=[
            ('/rtcm', '/ublox_dgnss/rtcm_in')  # Envoie les trames RTCM directement au ZED-F9P
        ]
    )

    return LaunchDescription([
        device_arg,
        ntrip_config_arg,
        ublox_launch,
        ntrip_node
    ])
