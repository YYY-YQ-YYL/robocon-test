# 操作手册（Operation Manual）

> 本工程采用开源标准仿真件（`robot` = 开源标准 burger 底盘，`robot_world` = 开源标准仿真世界），
> 覆盖 **双 SLAM 建图比较（Cartographer / SLAM Toolbox）** 与 **Navigation2 自主导航**。
> 下面每一步都在**独立终端**执行。所有 launch/节点命令可拆开单跑（见各节"独立命令"），
> 一键脚本只是把常用组合封装好。

前置约定（每个终端都要执行一次，脚本内已内置）：

```bash
export PATH=/usr/bin:/bin:$PATH    # 本机 conda python3 缺 rclpy/lxml，必须把系统 python 放最前
export ROBOT_MODEL=burger          # 选择 burger 模型/参数
source /opt/ros/humble/setup.bash
source ~/川山甲考核题/robot_ws/install/setup.bash
```

---

## 0. 环境与构建（终端 0）

```bash
cd ~/川山甲考核题
./scripts/00_build.sh            # colcon build --symlink-install（6 个包）
```

```bash
# 验证 6 个包已被识别
source robot_ws/install/setup.bash
ros2 pkg list | grep robot_
# 期望：robot_cartographer / robot_description / robot_gazebo /
#       robot_navigation / robot_slam_toolbox / robot_teleop
```

## 1. 启动 Gazebo 仿真（终端 1）

```bash
./scripts/01_start_simulation.sh
```

等效独立命令：
```bash
export PATH=/usr/bin:/bin:$PATH; export ROBOT_MODEL=burger
source /opt/ros/humble/setup.bash; source ~/川山甲考核题/robot_ws/install/setup.bash
ros2 launch robot_gazebo robot_world.launch.py
```

启动后约 5~10 秒出现小车（世界左侧，面向 +x）。

**自测（另开终端，先执行前置约定）：**

```bash
ros2 topic list | grep -E "scan|odom|clock|cmd_vel"   # 应有 /scan /odom /clock /cmd_vel
ros2 topic hz /scan                                   # 约 5.0 Hz
ros2 topic hz /odom                                   # 约 30 Hz
# TF 自测必须带 use_sim_time（TF 时间戳用仿真时钟）
ros2 run tf2_ros tf2_echo base_footprint base_scan --ros-args -p use_sim_time:=true
# 期望输出激光相对底盘的偏移（约 [-0.032, 0.000, 0.182]）
```

## 2. 键盘遥控（终端 2）

```bash
./scripts/02_teleop.sh
```

等效独立命令：
```bash
ros2 run robot_teleop robot_teleop_key
```

键位：`w` 前进 / `x` 后退 / `a` 左转 / `d` 右转 / `s` 停止（按住 shift 时更快）。保持该终端焦点。

## 3. 方法一：Cartographer 建图（终端 3）

```bash
./scripts/03_mapping_cartographer.sh
```

等效独立命令：
```bash
ros2 launch robot_cartographer cartographer.launch.py use_sim_time:=true
```

会另开 rviz2（固定帧 map）实时显示建图过程。**在终端 2 手动遥控小车巡游整个世界**，
建议走一条能形成回环的路线（绕场地外围一圈再穿行中间），以触发 Cartographer 的回环检测。

**自测：**

```bash
ros2 node list | grep cartographer      # cartographer_node / cartographer_occupancy_grid_node
ros2 topic hz /map                      # 建图更新时发布（publish_period 1.0s 左右）
ros2 run tf2_ros tf2_echo map base_footprint --ros-args -p use_sim_time:=true   # 有 map→odom TF
```

## 4. 保存方法一地图（终端 4，Cartographer 保持运行）

```bash
./scripts/05_save_map.sh robot_cartographer
```

等效独立命令：
```bash
ros2 run nav2_map_server map_saver_cli -f maps/robot_cartographer --occ 0.65 --free 0.25
```

生成 `maps/robot_cartographer.pgm` 与 `.yaml`。**必须此时保存**：`/map` 是 latched 话题，
SLAM 退出后无法再订阅到。

## 5. 方法二：SLAM Toolbox 建图（终端 3'）

**先 Ctrl+C 停掉 Cartographer（终端 3）**，再运行：

```bash
./scripts/04_mapping_slam_toolbox.sh
```

等效独立命令：
```bash
ros2 launch robot_slam_toolbox online_async_launch.py use_sim_time:=true
```

同样在终端 2 手动遥控小车巡游（**尽量走与 Cartographer 相同的轨迹**，保证对比公平）。

**自测：** 同上，确认 `async_slam_toolbox_node`、`/map`、map→odom TF 正常。

## 6. 保存方法二地图（终端 4，SLAM Toolbox 保持运行）

```bash
./scripts/05_save_map.sh robot_slam_toolbox
```

生成 `maps/robot_slam_toolbox.pgm` 与 `.yaml`。建图完成后 Ctrl+C 停掉 SLAM Toolbox。

## 7. Navigation2 自主导航（终端 5，需先停掉全部 SLAM）

加载哪张地图就传哪个名字（这里演示方法一的地图）：

```bash
./scripts/06_navigation.sh robot_cartographer
```

等效独立命令：
```bash
export ROBOT_MODEL=burger
ros2 launch robot_navigation navigation2.launch.py map:="$PWD/maps/robot_cartographer.yaml" use_sim_time:=true
```

在 rviz2 中：
1. `2D Pose Estimate`：给小车一个初始位姿（箭头方向与车头一致）；
2. `2D Goal Pose`：下达目标点，观察全局路径（绿色）与局部轨迹（蓝色），小车自主行驶。

**自测：**

```bash
ros2 node list | grep -E "amcl|planner|controller|bt_navigator|map_server"   # nav2 各节点
ros2 topic hz /cmd_vel                                      # 下达目标后应有速度输出
ros2 topic echo /amcl_pose --once --ros-args -p use_sim_time:=true
```

## 8. 双 SLAM 资源占用对比（可选，终端 4'）

建图期间另开终端采集 CPU/内存：

```bash
./scripts/07_measure_resources.sh cartographer_node 120         # 方法一建图期间
# …… Ctrl+C 停 Cartographer，换方法二建图期间再采：
./scripts/07_measure_resources.sh async_slam_toolbox_node 120   # 方法二建图期间
```

日志写到 `scripts/logs/top_<关键字>.log`，脚本末尾自动汇总均值。

## 9. 地图质量分析（对比数据，终端 6）

```bash
# 占用/空白/未知占比 + 墙连通分量
python3 scripts/analyze_map.py maps/robot_cartographer.pgm maps/robot_slam_toolbox.pgm

# 与理想世界（按 robot_world 设计坐标程序生成）求 IoU/Precision/Recall，并给两图一致性
python3 scripts/compare_maps.py maps/robot_cartographer.yaml maps/robot_slam_toolbox.yaml

# 把两张 PGM 地图转成可视化 PNG 图片（写报告/展示用，同名 .png）
python3 scripts/map_to_png.py maps/robot_cartographer.pgm maps/robot_slam_toolbox.pgm
```

结果填入 `docs/SLAM_Comparison.md` 的对比表格；PNG 图片可直接粘贴到报告截图栏。

## 10. 常见故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| 节点连不上 / TF 超时 | `use_sim_time` 未统一为 true | 所有 launch 传 `use_sim_time:=true` |
| rviz2 找不到 `map` 帧 | SLAM 未启动或已退出 | 建图阶段先启动 SLAM 再看 rviz；导航阶段启动 amcl |
| `/scan` 空消息 | 激光盲区/量程与 SLAM 参数不符 | 检查 SLAM `min/max_range` 是否 0.12/3.5 |
| slam_toolbox 报 pose_topic 错误 | `pose_topic` 被误设为 `/odom` | 保持默认 `pose`（slam_toolbox 靠 TF 取里程计） |
| 两个 SLAM 都开 → 地图混乱/TF 跳变 | 抢 `/map` 与 map→odom | 严格串行：停 A 再开 B |
| 地图保存为空/全灰 | SLAM 已退出，`/map` 不再发布 | 在 SLAM 存活时执行 `05_save_map` |
| 小车不动 | 遥控终端焦点被抢 | 保持终端 2 焦点，空格先停再 w |
| `spawn_entity.py` 报 `ModuleNotFoundError: lxml` | 终端 PATH 里 conda python 排前 | 本工程 launch 已设 `PATH=/usr/bin:/bin:$PATH`，确认启动前 export |
| 重复启动仿真时机器人导不进、gzserver 闪退(exit 255) | 上次 gzserver/gzclient 残留占用共享内存/端口 | `01_start_simulation.sh` 已自动清理；也可 `pkill -9 gzserver gzclient` 后再启动 |
| tf2_echo 报 `frame does not exist` | tf2_echo 默认用墙钟，而 TF 带仿真时钟戳 | 自测 tf2_echo 一律加 `--ros-args -p use_sim_time:=true` |
| 导航穿墙/抖动 | 初始位姿没给对 | 重新 2D Pose Estimate |
| Gazebo 卡顿 | 物理/渲染开销 | 建图时可在 launch 加 `use_rviz:=false` |

---

## 11. 录制视频建议流程（用户自录）

1. 录屏工具启动（如 GNOME 录屏 / OBS）。
2. 依次演示：
   1. 终端 0：`./scripts/00_build.sh`（构建）；
   2. 终端 1：`./scripts/01_start_simulation.sh`（Gazebo 世界与小车上电）；
   3. 终端 3：`./scripts/03_mapping_cartographer.sh` + 终端 2 遥控巡游 → 存图（05）→ 展示 rviz 地图；
   4. 停 Cartographer，终端 3'：`./scripts/04_mapping_slam_toolbox.sh` + 遥控巡游 → 存图（05）→ 展示 rviz 地图；
   5. 终端 5：`./scripts/06_navigation.sh robot_cartographer` → 2D Pose Estimate → 连续下达 3 个目标点 → 小车自主到达。
3. 若需要体现对比，可在第 2 步建图阶段同时运行 `07_measure_resources.sh` 采集 CPU/内存，最终把两套数据填入 `docs/SLAM_Comparison.md`。
4. 视频不随源码上交（按考核要求，源码已归类即可）。
