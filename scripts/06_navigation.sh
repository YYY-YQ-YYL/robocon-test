#!/usr/bin/env bash
# Navigation2 自主导航（AMCL 定位 + 全局规划 + DWB 局部规划 + 行为树执行）
# 前提：1) Gazebo 仿真运行中（终端 1）  2) 建图节点已关闭（Cartographer 或 SLAM Toolbox）
# 用法：./scripts/06_navigation.sh robot_cartographer   # 加载 05 保存的地图（也可传 robot_slam_toolbox）
set -e

NAME="${1:-robot_cartographer}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROBOT_WS="$ROOT/robot_ws"
MAP_YAML="$ROOT/maps/$NAME.yaml"

if [ ! -f "$MAP_YAML" ]; then
    echo "错误：找不到地图 $MAP_YAML"
    echo "请先运行 ./scripts/05_save_map.sh $NAME 保存地图"
    exit 1
fi

export PATH=/usr/bin:/bin:$PATH
export ROBOT_MODEL=burger
source /opt/ros/humble/setup.bash
source "$ROBOT_WS/install/setup.bash"

ros2 launch robot_navigation navigation2.launch.py \
    map:="$MAP_YAML" use_sim_time:=true
