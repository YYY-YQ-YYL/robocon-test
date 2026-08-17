#!/usr/bin/env bash
# 键盘遥控小车（发布 /cmd_vel），用于手动巡游建图与导航演示
# 终端 2 运行本脚本，保持该终端焦点
# 键位（robot_teleop 的键盘遥控，步进式调速）：
#   w 前进    x 后退    a 左转    d 右转    s 停止；按住 shift 时 w/x 更快
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROBOT_WS="$ROOT/robot_ws"

export PATH=/usr/bin:/bin:$PATH
source /opt/ros/humble/setup.bash
source "$ROBOT_WS/install/setup.bash"

ros2 run robot_teleop robot_teleop_key
