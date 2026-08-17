#!/usr/bin/env bash
# 保存当前 /map 到顶层 maps/（占用栅格 -> .pgm + .yaml）
# 注意：必须在【对应 SLAM 节点存活】时执行（/map 是 latched 话题，
#       SLAM 退出后无法再被订阅保存）。
# 用法：./scripts/05_save_map.sh robot_cartographer   # 保存 Cartographer 建的地图
#       ./scripts/05_save_map.sh robot_slam_toolbox   # 保存 SLAM Toolbox 建的地图
set -e

NAME="${1:-robot_cartographer}"   # 文件名前缀：建议用 SLAM 方法名区分

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROBOT_WS="$ROOT/robot_ws"
MAPS_DIR="$ROOT/maps"
mkdir -p "$MAPS_DIR"

export PATH=/usr/bin:/bin:$PATH
source /opt/ros/humble/setup.bash
source "$ROBOT_WS/install/setup.bash"

ros2 run nav2_map_server map_saver_cli \
    -f "$MAPS_DIR/$NAME" \
    --occ 0.65 --free 0.25 \
    --ros-args -p save_map_timeout:=5.0

echo "已保存：$MAPS_DIR/$NAME.pgm 与 $MAPS_DIR/$NAME.yaml"
echo "对比分析：python3 scripts/compare_maps.py maps/robot_cartographer.yaml maps/robot_slam_toolbox.yaml"
