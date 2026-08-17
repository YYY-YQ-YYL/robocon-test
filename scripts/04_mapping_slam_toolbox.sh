#!/usr/bin/env bash
# 拓展 SLAM 方案：SLAM Toolbox 建图（方法二）
# 重要：必须【先 Ctrl+C 停掉 Cartographer（终端 3）】再运行本脚本！
#       两个 SLAM 同时运行会争抢 /map 与 map->odom TF，导致建图错乱。
# 建图方式与 Cartographer 相同：终端 2 遥控巡游，终端 3 观察 rviz2。
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROBOT_WS="$ROOT/robot_ws"

export PATH=/usr/bin:/bin:$PATH
source /opt/ros/humble/setup.bash
source "$ROBOT_WS/install/setup.bash"

ros2 launch robot_slam_toolbox online_async_launch.py use_sim_time:=true
