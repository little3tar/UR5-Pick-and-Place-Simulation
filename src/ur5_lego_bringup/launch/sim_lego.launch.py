"""UR5 + Robotiq 2F-85 + Lego world (Gazebo Harmonic)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    IfElseSubstitution,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    gz_share = get_package_share_directory('ur5_lego_gazebo')
    desc_share = get_package_share_directory('ur5_lego_description')
    world = os.path.join(gz_share, 'worlds', 'main_scene.sdf')
    description_file = os.path.join(desc_share, 'urdf', 'ur5_lego_gz.urdf.xacro')
    controllers_file = os.path.join(desc_share, 'config', 'ur_lego_controllers.yaml')

    models_lego = os.path.join(gz_share, 'models', 'lego')
    models_scene = os.path.join(gz_share, 'models', 'scene')
    existing = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    resource_path = f'{models_lego}:{models_scene}'
    if existing:
        resource_path = f'{resource_path}:{existing}'

    ur_type = LaunchConfiguration('ur_type')
    gazebo_gui = LaunchConfiguration('gazebo_gui')
    launch_rviz = LaunchConfiguration('launch_rviz')
    activate_joint_controller = LaunchConfiguration('activate_joint_controller')
    initial_joint_controller = LaunchConfiguration('initial_joint_controller')

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ', description_file,
        ' ', 'name:=ur',
        ' ', 'ur_type:=', ur_type,
        ' ', 'tf_prefix:=',
        ' ', 'simulation_controllers:=', controllers_file,
        ' ', 'with_gripper:=true',
    ])
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str),
    }

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[{'use_sim_time': True}, robot_description],
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
    )

    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[initial_joint_controller, '-c', '/controller_manager'],
        condition=IfCondition(activate_joint_controller),
    )

    gz_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-string', robot_description_content,
            '-name', 'ur',
            '-allow_renaming', 'true',
        ],
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py',
            ])
        ),
        launch_arguments={
            'gz_args': IfElseSubstitution(
                gazebo_gui,
                if_value=[' -r -v 4 ', world],
                else_value=[' -s -r -v 4 ', world],
            ),
        }.items(),
    )

    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/gripper_left_cmd@std_msgs/msg/Float64]gz.msgs.Double',
            '/gripper_right_cmd@std_msgs/msg/Float64]gz.msgs.Double',
        ],
        output='screen',
    )

    attach_node = Node(
        package='ur5_lego_attach',
        executable='attach_node',
        name='ur5_lego_attach',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'world': 'ur5_world',
            'default_parent_frame': 'robotiq_85_base_link',
            'tf_root': 'world',
            'rate_hz': 30.0,
            'mode': 'snap',
            'snap_offset_z': 0.12,
        }],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='log',
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('ur_type', default_value='ur5'),
        DeclareLaunchArgument('gazebo_gui', default_value='true'),
        DeclareLaunchArgument('launch_rviz', default_value='false'),
        DeclareLaunchArgument('activate_joint_controller', default_value='true'),
        DeclareLaunchArgument(
            'initial_joint_controller',
            default_value='scaled_joint_trajectory_controller',
        ),
        SetEnvironmentVariable(name='GZ_SIM_RESOURCE_PATH', value=resource_path),
        SetEnvironmentVariable(name='IGN_GAZEBO_RESOURCE_PATH', value=resource_path),
        robot_state_publisher,
        gz_sim,
        gz_spawn_entity,
        gz_bridge,
        joint_state_broadcaster_spawner,
        arm_controller_spawner,
        attach_node,
        rviz,
    ])
