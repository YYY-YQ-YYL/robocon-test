#!/usr/bin/env bash
# 基础 SLAM 方案：Cartographer 建图（方法一）
# 终端 3 运行本脚本（会另开 rviz2，固定帧 map 实时显示建图过程），
# 然后在终端 2 遥控小车巡游整个世界，走完闭环触发回环检测。
# 存图前【保持本终端运行】——SLAM 节点退出后 /map 不再更新。
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROBOT_WS="$ROOT/robot_ws"

export PATH=/usr/bin:/bin:$PATH
source /opt/ros/humble/setup.bash
source "$ROBOT_WS/install/setup.bash"

ros2 launch robot_cartographer cartographer.launch.py use_sim_time:=true
