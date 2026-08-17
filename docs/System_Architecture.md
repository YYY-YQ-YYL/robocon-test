# 系统架构说明（System Architecture）

本工程为 **方向二：自主导航** 的仿真工程，完整实现：移动机器人→ Gazebo 仿真世界→ 双 SLAM 建图（Cartographer 、 SLAM Toolbox）→ 保存地图 → Navigation2 自主导航。本文档说明整体架构、节点、Topic、TF 树、参数体系与各模块原理。

---
## 1. 节点清单

| 阶段 | 节点 | 包 | 作用 |
|---|---|---|---|
| 仿真 | `gzserver` / `gzclient` | gazebo | 物理仿真：运行 `robot_world` 世界、机器人刚体、传感器插件 |
| 仿真 | `robot_state_publisher` | robot_state_publisher | 解析 URDF，结合 `/joint_states` 发布 base_footprint→base_link 等静态 TF |
| 仿真 | `spawn_entity.py` | gazebo_ros | 把 `robot_description` 参数里的模型 spawn 进 Gazebo 世界 |
| 仿真 | `robot_diff_drive`（插件） | gazebo_plugins | 订阅 `/cmd_vel` → 驱动左右轮 → 发布 `/odom` 与 odom→base_footprint TF |
| 仿真 | `robot_laserscan`（插件） | gazebo_plugins | 360° 2D 激光（LDS-01），发布 `/scan`（LaserScan，5Hz） |
| 仿真 | `robot_imu`（插件） | gazebo_plugins | 发布 `/imu`（硬件在位；双 SLAM 均未消费，仅保证信息完整） |
| 遥控 | `robot_teleop_key` | robot_teleop | 键盘发布 `/cmd_vel`，供建图/测试 |
| 建图方法一 | `cartographer_node` | cartographer_ros | 激光+里程计 → 局部子图与全局位姿，发布 map→odom TF |
| 建图方法一 | `cartographer_occupancy_grid_node` | cartographer_ros | 把 Cartographer 轨迹栅格化为 `/map` OccupancyGrid |
| 建图方法二 | `async_slam_toolbox_node` | slam_toolbox | 在线异步建图，发布 map→odom TF 与 `/map` |
| 定位 | `map_server` | nav2_map_server | 加载 `.yaml/.pgm` 地图为 `/map`；`amcl` 在其上定位 |
| 定位 | `amcl` | nav2_amcl | 自适应蒙特卡洛定位，发布 map→odom TF 与 `/amcl_pose` |
| 规划 | `planner_server` | nav2_planner | 全局路径规划（NavFn，A*） |
| 规划 | `controller_server` | nav2_controller | 局部路径跟踪（DWB 采样）与避障，发布 `/cmd_vel` |
| 规划 | `bt_navigator` | nav2_bt_navigator | 行为树编排：导航/跟随等任务 |
| 规划 | `costmap_2d` ×2 | nav2_costmap_2d | 全局/局部代价地图（障碍层+膨胀层） |

## 2. TF 树

```
map ──(SLAM/AMCL: map→odom)──► odom ──(diff_drive: odom→base_footprint)──► base_footprint
                                                                            │
                                                                            └──► base_link
                                                                                  ├──► wheel_left_link   (wheel_left_joint,  continuous)
                                                                                  ├──► wheel_right_link  (wheel_right_joint, continuous)
                                                                                  ├──► caster_back_link  (caster_back_joint, fixed)
                                                                                  ├──► imu_link          (imu_joint,      fixed)
                                                                                  └──► base_scan         (scan_joint,     fixed)
```

- **map→odom**：建图阶段由 `cartographer_node` / `async_slam_toolbox_node` 发布（全局修正，闭环时跳变）；导航阶段由 `amcl` 发布（概率定位）。
- **odom→base_footprint**：始终由 Gazebo `diff_drive` 插件发布（车轮里程计）。
- **base_footprint→base_link→子帧**：由 `robot_state_publisher` + `/joint_states` 发布；固定关节直接静态。

> 关键：SLAM 与 AMCL **绝不同时发布 map→odom**。因此建图、导航必须串行切换。

## 3. 话题清单

| 话题 | 类型 | 方向 | 发布者 → 订阅者 |
|---|---|---|---|
| `/cmd_vel` | geometry_msgs/Twist | 下 | teleop / controller_server → diff_drive |
| `/odom` | nav_msgs/Odometry | 上 | diff_drive → nav2 / SLAM |
| `/scan` | sensor_msgs/LaserScan | 上 | laser 插件 → amcl / SLAM / costmap |
| `/joint_states` | sensor_msgs/JointState | 上 | joint_state 插件 → robot_state_publisher |
| `/imu` | sensor_msgs/Imu | 上 | imu 插件 → （备用，双 SLAM 均 use_imu_data=false） |
| `/map` | nav_msgs/OccupancyGrid | 上 | SLAM / map_server → 可视化、amcl |
| `/map_metadata` | nav_msgs/MapMetaData | 上 | 随 `/map` 同发 |
| `/clock` | rosgraph_msgs/Clock | 上 | gzserver → 全部 use_sim_time 节点 |
| `/tf` | tf2_msgs/TFMessage | 上 | 上述各发布方 → 所有需要 TF 的节点 |
| `/tf_static` | tf2_msgs/TFMessage | 上 | robot_state_publisher → 各节点 |
| `/initialpose` | geometry_msgs/PoseWithCovarianceStamped | 下 | rviz2 → amcl |
| `/goal_pose` | geometry_msgs/PoseStamped | 下 | rviz2 → bt_navigator |
| `/amcl_pose` | geometry_msgs/PoseWithCovarianceStamped | 上 | amcl → rviz2 |
| `/plan` | nav_msgs/Path | 上 | planner → rviz2 |

## 4. 关键参数体系

### 4.1 传感器（robot_gazebo/models/robot_burger/model.sdf，官方 LDS-01 + 差速底盘）
- 激光：360 采样、`min_angle 0`、`max_angle 6.28`（≈360°）、`min 0.12m / max 3.5m`、`update_rate 5Hz`、`frame_name base_scan`、高斯噪声 σ=0.01、安装偏移 (-0.032, 0, 0.171)m。
- 差速：`wheel_separation 0.160`、`wheel_diameter 0.066`、`max_wheel_torque 20`、`update_rate 30`，`command_topic cmd_vel`、`odometry_topic odom`、`robot_base_frame base_footprint`。
- IMU：`update_rate` 默认，发布 `/imu`（仅备用，未消费）。

### 4.2 Cartographer（方法一，robot_cartographer/config/robot_lds_2d.lua，官方配置）
- `tracking_frame = "imu_link"`：以 IMU 帧为跟踪帧（官方默认，随 URDF 静态 TF 提供）。
- `published_frame = "odom"`、`provide_odom_frame = false`：Cartographer 只发布 map→odom。
- `use_odometry = true`、`use_imu_data = false`：仅里程计输入。
- `min_range = 0.12 / max_range = 3.5`：与激光量程对齐。
- `missing_data_ray_length = 3.0`：无回波方向按最大量程补边。
- `map_builder.lua` / `trajectory_builder.lua` 为官方默认文件，随包复制保证自包含。

### 4.3 SLAM Toolbox（方法二，robot_slam_toolbox/config/mapper_params_online_async.yaml）
- `odom_frame: odom`、`map_frame: map`、`base_frame: base_footprint`：TF 口径对齐。
- `scan_topic: /scan`、`mode: mapping`、`resolution: 0.05`。
- `min_laser_range: 0.12`、`max_laser_range: 3.5`：对齐传感器量程（官方默认 12m，会导致空扫）。
- `do_loop_closing: true`、`map_update_interval: 2.0`、`transform_publish_period: 0.02`。
- `minimum_travel_distance: 0.2`：低速场景避免同一位置反复回环判定。
- **`pose_topic` 保持默认 `pose`**：slam_toolbox 通过 TF 取里程计，`pose_topic` 仅收 PoseStamped，设为 `/odom`（Odometry 消息）会直接报错。
- solver 使用官方 CeresSolver 参数（`LEVENBERG_MARQUARDT` 信任策略）。

### 4.4 Navigation2（robot_navigation/param/robot.yaml，官方 humble/burger 参数）
- `use_sim_time`：launch 传入 `use_sim_time:=true` 覆盖到各节点（官方样例默认 False，仿真必须改）。
- `amcl`：`base_frame_id: base_footprint`、`global_frame_id: map`、`odom_frame_id: odom`、`scan_topic: scan`。
- `bt_navigator`：`robot_base_frame: base_link`、`odom_topic: /odom`。
- controller_server / costmap：`robot_base_frame: base_link`（与 TF 一致），DWB 速度上限 `max_vel_x 0.22 / max_vel_theta 1.0`（官方 burger 值）。
- 其余（planner、behavior server、waypoint 等）均为官方默认，未改动。

### 4.5 存图（map_saver_cli）
- `--occ 0.65 --free 0.25`：占用概率 >0.65 计为障碍、<0.25 计为空闲（**注意 ROS 2 取值为 0.0~1.0 概率，不是百分比**）。


