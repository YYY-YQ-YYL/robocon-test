# 川山甲考核 自主导航
- **2.1 普通题**：移动机器人+ 仿真世界+ Navigation2 自主导航部署
- **2.2 拓展题**：部署第二种开源 SLAM —— **SLAM Toolbox**（方法二），与基础方案 **Cartographer**（方法一）在同一环境下对比

## 1. 工程结构

```
川山甲考核题/
├── README.md                  ← 本文件
├── docs/
│   ├── System_Architecture.md ← 系统架构：节点图 / TF 树 / 话题表 / 参数 / 原理
│   ├── Operation_Manual.md    ← 操作手册：每个节点的终端命令 + 自测 + 故障排查 + 录视频流程
│   ├── SLAM_Comparison.md     ← 双 SLAM 对比报告（实测数据 + 结论）
│   ├── Development_Record.md  ← 开发记录：AI 辅助说明 + 失败案例(真实报错) + 实测数据 + 素材归档
│   └── screenshots/           ← 运行截图（建图/Gazebo/RViz，待使用者补充）
├── scripts/                   ← 一键命令脚本与对比分析工具
│   ├── 00_build.sh             构建工作空间
│   ├── 01_start_simulation.sh  Gazebo 世界 + 机器人
│   ├── 02_teleop.sh            键盘遥控
│   ├── 03_mapping_cartographer.sh   方法一建图（Cartographer）
│   ├── 04_mapping_slam_toolbox.sh   方法二建图（SLAM Toolbox）
│   ├── 05_save_map.sh          保存 /map 为 pgm+yaml 到 maps/
│   ├── 06_navigation.sh        启动 Navigation2 自主导航
│   ├── 07_measure_resources.sh 采集 SLAM 进程 CPU/内存
│   ├── analyze_map.py          地图占用/未知占比 + 障碍连通块统计
│   ├── compare_maps.py         双 SLAM 与理想世界 IoU/Precision/Recall
│   └── map_to_png.py           PGM 地图转可视化 PNG 图片（写报告/展示用）
├── maps/                      ← 两次建图保存的地图（robot_cartographer / robot_slam_toolbox）
└── robot_ws/src/              ← ROS 2 源码（6 个包）
    ├── robot_description/      机器人描述（URDF + 网格 + RViz）
    ├── robot_gazebo/           仿真（世界 + 机器人模型 + 启动链）
    ├── robot_cartographer/     基础 SLAM：Cartographer（方法一）
    ├── robot_slam_toolbox/     拓展 SLAM：SLAM Toolbox（方法二）
    ├── robot_navigation/       Navigation2 自主导航（AMCL + 规划器 + 参数）
    └── robot_teleop/           键盘遥控
```

## 2. 环境依赖

- Ubuntu 22.04 + **ROS 2 Humble**（`ros-humble-desktop`）
- Gazebo Classic 11（`gazebo_ros`、`gazebo_plugins`）
- `cartographer_ros`、`slam_toolbox`、`nav2_*` 全套、`robot_state_publisher`、`map_server`
- colcon / rviz2

## 3. 操作流程

```bash
# 终端 0：构建
cd ~/川山甲考核题 && ./scripts/00_build.sh

# 终端 1：启动仿真（Gazebo 世界 + 机器人）
./scripts/01_start_simulation.sh

# 终端 2：键盘遥控
./scripts/02_teleop.sh

# —— 方法一：Cartographer 建图 ——
# 终端 3：
./scripts/03_mapping_cartographer.sh
# 终端 2 遥控巡游整个世界（走回环路线）
# 终端 4（Cartographer 保持运行）：
./scripts/05_save_map.sh robot_cartographer

# —— 方法二：SLAM Toolbox 建图——
# 终端 3'：
./scripts/04_mapping_slam_toolbox.sh
# 终端 2 再次遥控巡游
# 终端 4（SLAM Toolbox 保持运行）：
./scripts/05_save_map.sh robot_slam_toolbox

# —— 对比分析（终端 6）——
python3 scripts/analyze_map.py maps/robot_cartographer.pgm maps/robot_slam_toolbox.pgm
python3 scripts/compare_maps.py maps/robot_cartographer.yaml maps/robot_slam_toolbox.yaml

# —— 导航——
./scripts/06_navigation.sh robot_cartographer   # 或 robot_slam_toolbox
```

## 5. 双 SLAM 对比要点

| 维度 | 方法一：Cartographer | 方法二：SLAM Toolbox |
|---|---|---|
| 定位原理 | 前端 CSM 扫描匹配 + 后端 Pose Graph 图优化 | 前端扫描匹配 + 后端 KartoGraph（SPA）图优化 |
| 配置 | Lua（含官方 include 文件） | 单个 YAML |
| 调参成本 | 高 | 低 |
| 典型适用 | 复杂/大场景、传感器噪声大 | 中小场景、快速部署 |

定量指标（地图质量 IoU、Precision、Recall由 `analyze_map.py`、
`compare_maps.py`、`07_measure_resources.sh` 产出，模板与结论框架见 `docs/SLAM_Comparison.md`。

## 6. 相关文档

- 系统架构（节点/TF/话题/参数/原理）：[docs/System_Architecture.md](docs/System_Architecture.md)
- 双 SLAM 对比报告（实测数据 + 结论）：[docs/SLAM_Comparison.md](docs/SLAM_Comparison.md)
- 开发记录：[docs/Development_Record.md](docs/Development_Record.md)
