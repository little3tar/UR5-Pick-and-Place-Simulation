"""Bringup: lego world (+ optional level spawn later)."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    gazebo_launch = os.path.join(
        get_package_share_directory('ur5_lego_gazebo'),
        'launch', 'lego_world.launch.py',
    )
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gazebo_launch)),
    ])
