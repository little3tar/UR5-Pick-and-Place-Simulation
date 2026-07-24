"""Launch Gazebo Harmonic with Lego scene (no robot yet)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    gz_share = get_package_share_directory('ur5_lego_gazebo')
    world = os.path.join(gz_share, 'worlds', 'main_scene.sdf')
    models_lego = os.path.join(gz_share, 'models', 'lego')
    models_scene = os.path.join(gz_share, 'models', 'scene')

    # Append (do not overwrite) so system models still resolve later
    existing = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    resource_path = f'{models_lego}:{models_scene}'
    if existing:
        resource_path = f'{resource_path}:{existing}'

    gui = LaunchConfiguration('gui')
    declare_gui = DeclareLaunchArgument(
        'gui', default_value='true',
        description='Start Gazebo GUI (false = headless -s)',
    )

    set_gz_res = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=resource_path,
    )
    set_ign_res = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=resource_path,
    )

    gz_launch = os.path.join(
        get_package_share_directory('ros_gz_sim'),
        'launch', 'gz_sim.launch.py',
    )

    gz_sim_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={'gz_args': ['-r ', world]}.items(),
        condition=IfCondition(gui),
    )
    gz_sim_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={'gz_args': ['-r -s ', world]}.items(),
        condition=UnlessCondition(gui),
    )

    return LaunchDescription([
        declare_gui,
        set_gz_res,
        set_ign_res,
        gz_sim_gui,
        gz_sim_headless,
    ])
