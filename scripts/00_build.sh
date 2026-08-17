#!/usr/bin/env bash
# 构建 robot_ws 工作空间（colcon build）
# 用法：./scripts/00_build.sh
# 说明：本机 conda 的 python3 在前，缺少 rclpy/lxml，必须把 /usr/bin 放最前，
#       否则 colcon / spawn_entity.py 会因 python 解释器解析错误而失败。
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROBOT_WS="$ROOT/robot_ws"

export PATH=/usr/bin:/bin:$PATH
source /opt/ros/humble/setup.bash

# 首次或改动后干净重建：rm -rf "$ROBOT_WS"/{build,install,log}
colcon --log-base "$ROBOT_WS/log" build --symlink-install \
    --base-paths "$ROBOT_WS/src" \
    --build-base "$ROBOT_WS/build" \
    --install-base "$ROBOT_WS/install" \
    "$@"

echo "构建完成。验证："
echo "  source $ROBOT_WS/install/setup.bash"
echo "  ros2 pkg list | grep robot_   # 应看到 6 个包"
