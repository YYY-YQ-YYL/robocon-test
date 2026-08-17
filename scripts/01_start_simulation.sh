#!/usr/bin/env bash
# 启动标准仿真环境：Gazebo 世界（robot_world）+ 机器人（burger 底盘，URDF robot_burger）
# 终端 1 运行本脚本；启动后约 5~10 秒出现小车（世界左侧，面向 +x）。
# 环境说明：机器人本体与世界均采用开源标准配置，仅统一命名（robot）。
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROBOT_WS="$ROOT/robot_ws"

export PATH=/usr/bin:/bin:$PATH          # 规避 conda python 缺 rclpy/lxml
export ROBOT_MODEL=burger                # 选择 burger 模型/参数（被 spawn/RSP/nav2 读取）
source /opt/ros/humble/setup.bash
source "$ROBOT_WS/install/setup.bash"

# 清理上次残留进程（否则新 gzserver 会因共享内存冲突直接退出）
# pkill 无匹配时返回 1，需 || true 否则 set -e 终止脚本
pkill -9 -f "gzserver" 2>/dev/null || true
pkill -9 -f "gzclient" 2>/dev/null || true
pkill -9 -f "ros2 launch robot_gazebo" 2>/dev/null || true
pkill -9 -f "spawn_entity.py" 2>/dev/null || true
sleep 1

ros2 launch robot_gazebo robot_world.launch.py
