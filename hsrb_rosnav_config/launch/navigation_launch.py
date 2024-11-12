#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def declare_arguments():
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            'namespace', default_value='',
            description='Top-level namespace'))

    declared_arguments.append(
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Use simulation (Gazebo) clock if true'))

    # declared_arguments.append(
    #     DeclareLaunchArgument(
    #         'initial_pose_x', default_value='0',
    #         description='Initial x position of the robot'))

    # declared_arguments.append(
    #     DeclareLaunchArgument(
    #         'initial_pose_y', default_value='0',
    #         description='Initial y position of the robot'))

    # declared_arguments.append(
    #     DeclareLaunchArgument(
    #         'initial_pose_z', default_value='0',
    #         description='Initial z position of the robot'))

    # declared_arguments.append(
    #     DeclareLaunchArgument(
    #         'initial_pose_yaw', default_value='0',
    #         description='Initial yaw of the robot'))

    declared_arguments.append(
        DeclareLaunchArgument(
            'autostart', default_value='true',
            description='Automatically startup the nav2 stack'))

    declared_arguments.append(
        DeclareLaunchArgument(
            'map',
            description='Full path to map yaml file to load'))

    declared_arguments.append(
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(get_package_share_directory('hsrb_rosnav_config'),
                                       'config', 'nav2_params.yaml'),
            description='Full path to the ROS2 parameters file to use'))

    declared_arguments.append(
        DeclareLaunchArgument(
            'default_bt_xml_filename',
            default_value=os.path.join(
                get_package_share_directory('nav2_bt_navigator'),
                'behavior_trees', 'navigate_w_replanning_and_recovery.xml'),
            description='Full path to the behavior tree xml file to use'))

    declared_arguments.append(
        DeclareLaunchArgument(
            'map_subscribe_transient_local', default_value='true',
            description='Whether to set the map subscriber QoS to transient local'))

    return declared_arguments


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    map_yaml_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    default_bt_xml_filename = LaunchConfiguration('default_bt_xml_filename')
    map_subscribe_transient_local = LaunchConfiguration('map_subscribe_transient_local')
    # initial_pose_x = LaunchConfiguration('initial_pose_x')
    # initial_pose_y = LaunchConfiguration('initial_pose_y')
    # initial_pose_z = LaunchConfiguration('initial_pose_z')
    # initial_pose_yaw = LaunchConfiguration('initial_pose_yaw')

    lifecycle_nodes = ['controller_server',
                       'planner_server',
                       'behavior_server',
                       'bt_navigator',
                       'waypoint_follower']

    tf_remappings = [('/tf', 'tf'),
                     ('/tf_static', 'tf_static')]
    velocity_remappings = [('cmd_vel', 'omni_base_controller/cmd_vel')]
    remappings = tf_remappings + velocity_remappings

    param_substitutions = {
        'use_sim_time': use_sim_time,
        # we want to set the initial pose from the launch argument here,
        # but not work because we have no way to hand this to localization_launch.py
        # 'initial_pose.x': initial_pose_x,
        # 'initial_pose.y': initial_pose_y,
        # 'initial_pose.z': initial_pose_z,
        # 'initial_pose.yaw': initial_pose_yaw,
        'default_bt_xml_filename': default_bt_xml_filename,
        'autostart': autostart,
        'map_subscribe_transient_local': map_subscribe_transient_local}

    configured_params = RewrittenYaml(
        source_file=params_file,
        root_key=namespace,
        param_rewrites=param_substitutions,
        convert_types=True)

    env = SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('nav2_bringup'),
                                                   'launch',
                                                   'localization_launch.py')),
        launch_arguments={'namespace': namespace,
                          'map': map_yaml_file,
                          'use_sim_time': use_sim_time,
                          'autostart': autostart,
                          'params_file': params_file}.items())

    controller_server_node = Node(
        package='nav2_controller',
        executable='controller_server',
        output='screen',
        parameters=[configured_params],
        remappings=remappings)

    planner_server_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[configured_params],
        remappings=tf_remappings)

    behavior_server_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[configured_params],
        remappings=remappings)

    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[configured_params],
        remappings=tf_remappings)

    waypoint_follower_node = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[configured_params],
        remappings=tf_remappings)

    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time},
                    {'autostart': autostart},
                    {'node_names': lifecycle_nodes}])

    nodes = [
        env,
        localization_launch,
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,
        waypoint_follower_node,
        lifecycle_manager_node
    ]

    return LaunchDescription(declare_arguments() + nodes)
