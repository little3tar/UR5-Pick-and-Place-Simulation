"""Smoke launch: official UR Gazebo sim (ur_simulation_gz).

Phase 0 entry point. Full lego world comes in later phases.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    ur_type = LaunchConfiguration('ur_type')
    declare_ur = DeclareLaunchArgument(
        'ur_type', default_value='ur5',
        description='UR type: ur3, ur5, ur10, ur3e, ur5e, ...'
    )

    sim_share = get_package_share_directory('ur_simulation_gz')
    # try common launch file names across package versions
    candidates = [
        'ur_sim_control.launch.py',
        'ur_sim.launch.py',
    ]
    launch_file = None
    for name in candidates:
        path = os.path.join(sim_share, 'launch', name)
        if os.path.isfile(path):
            launch_file = path
            break

    if launch_file is None:
        return LaunchDescription([
            declare_ur,
            LogInfo(msg='ur_simulation_gz launch file not found; install ros-jazzy-ur-simulation-gz'),
        ])

    return LaunchDescription([
        declare_ur,
        LogInfo(msg=['Starting official UR sim: ', launch_file]),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_file),
            launch_arguments={'ur_type': ur_type}.items(),
        ),
    ])
