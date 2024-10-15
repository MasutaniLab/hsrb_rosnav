#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
    TimerAction,
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
            'map_subscribe_transient_local', default_value='false',
            description='Whether to set the map subscriber QoS to transient local'))

    return declared_arguments


def launch_setup(context,
                 namespace,
                 use_sim_time,
                 initial_orientation_xyzw,
                 autostart,
                 map_yaml_file,
                 params_file,
                 default_bt_xml_filename,
                 map_subscribe_transient_local):

    initial_orientation_xyzw_list = context.perform_substitution(initial_orientation_xyzw).split(',')
    orientation = f'x: {initial_orientation_xyzw_list[0]}, y: {initial_orientation_xyzw_list[1]}, \
                    z: {initial_orientation_xyzw_list[2]}, w: {initial_orientation_xyzw_list[3]}'

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
        'default_bt_xml_filename': default_bt_xml_filename,
        'autostart': autostart,
        'map_subscribe_transient_local': map_subscribe_transient_local}

    configured_params = RewrittenYaml(
        source_file=params_file,
        root_key=namespace,
        param_rewrites=param_substitutions,
        convert_types=True)

    set_initial_cmd = ExecuteProcess(
        cmd=[[
            'ros2 ',
            'topic pub -1 ',
            '/initialpose geometry_msgs/PoseWithCovarianceStamped ',
            '\'{ header: {stamp: {sec: 0, nanosec: 0}, frame_id: "map"}, ',
            'pose: { pose: {position: {x: 0.0, y: 0.0, z: 0.0}, ',
            'orientation: {',
            f'{orientation}',
            '}, } } }\''
        ]],
        shell=True
    )

    set_initial_cmd_delay = TimerAction(
        period=20.0,
        actions=[set_initial_cmd]
    )

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
        lifecycle_manager_node,
        set_initial_cmd_delay
    ]

    return nodes


def generate_launch_description():

    return LaunchDescription(declare_arguments() + [
        OpaqueFunction(function=launch_setup,
                       args=[LaunchConfiguration('namespace'),
                             LaunchConfiguration('use_sim_time'),
                             LaunchConfiguration('initial_orientation_xyzw'),
                             LaunchConfiguration('autostart'),
                             LaunchConfiguration('map'),
                             LaunchConfiguration('params_file'),
                             LaunchConfiguration('default_bt_xml_filename'),
                             LaunchConfiguration('map_subscribe_transient_local')])])
