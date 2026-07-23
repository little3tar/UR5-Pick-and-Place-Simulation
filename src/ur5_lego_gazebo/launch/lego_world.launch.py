"""Launch Gazebo Harmonic with Lego scene (no robot yet)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    gz_share = get_package_share_directory('ur5_lego_gazebo')
    world = os.path.join(gz_share, 'worlds', 'main_scene.sdf')
    models_lego = os.path.join(gz_share, 'models', 'lego')
    models_scene = os.path.join(gz_share, 'models', 'scene')
    resource_path = f'{models_lego}:{models_scene}'

    gui = LaunchConfiguration('gui')
    declare_gui = DeclareLaunchArgument('gui', default_value='true')

    # Append model paths for model:// resolution
    set_gz_res = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=resource_path,
    )
    # also classic-compat var some tools still read
    set_ign_res = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=resource_path,
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch', 'gz_sim.launch.py',
            )
        ),
        launch_arguments={
            'gz_args': ['-r ', world],
        }.items(),
    )

    return LaunchDescription([
        declare_gui,
        set_gz_res,
        set_ign_res,
        gz_sim,
    ])
