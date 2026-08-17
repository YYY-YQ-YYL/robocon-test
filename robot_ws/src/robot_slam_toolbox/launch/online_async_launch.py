# Copyright 2026, robot_slam_toolbox
# Licensed under the Apache License, Version 2.0
#
# 拓展 SLAM 方案：SLAM Toolbox 在线异步建图
# 用法：ros2 launch robot_slam_toolbox online_async_launch.py use_sim_time:=true
# 前提：Gazebo 仿真已启动；且必须先停掉 Cartographer（两个 SLAM 会争抢 /map 与 map->odom TF）

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_slam_toolbox_prefix = get_package_share_directory('robot_slam_toolbox')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    slam_params_file = LaunchConfiguration(
        'slam_params_file',
        default=os.path.join(
            robot_slam_toolbox_prefix, 'config', 'mapper_params_online_async.yaml'))

    rviz_config = os.path.join(robot_slam_toolbox_prefix, 'rviz', 'slam_toolbox.rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation/Gazebo clock'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=slam_params_file,
            description='Full path to the slam_toolbox parameters file'),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch rviz2 for mapping view'),

        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[
                slam_params_file,
                {'use_sim_time': use_sim_time},
            ],
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(use_rviz),
        ),
    ])
