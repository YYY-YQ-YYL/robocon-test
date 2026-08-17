import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    robot_description_dir = get_package_share_directory('robot_description')
    urdf_path = os.path.join(robot_description_dir, 'urdf', 'robot_burger.urdf')
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_desc}]),
        Node(package='rviz2', executable='rviz2',
             arguments=['-d', os.path.join(robot_description_dir, 'rviz', 'model.rviz')]),
    ])
