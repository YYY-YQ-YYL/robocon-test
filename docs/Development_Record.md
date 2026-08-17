# 开发记录（Development Record）

> 本文件如实记录本工程从搭建到双 SLAM 建图对比的完整开发过程：
> 里程碑、**AI 辅助使用说明**、**关键失败案例（含真实终端报错）**、实测数据与产物归档。
> 素材原则：**只保留具有实际意义的材料**（终端报错、运行/仿真截图、实测数据、失败案例），不堆砌流水账。

| 项 | 内容 |
|---|---|
| 项目 | 方向二：自主导航（ROS 2 Humble + Gazebo Classic 仿真） |
| 工作空间 | `~/川山甲考核题/robot_ws`（6 个 `robot_*` 包） |
| 环境 | Ubuntu 22.04 / ROS 2 Humble / Gazebo Classic 11 / Python 3.10 |
| 开发周期 | 单次集中开发 + 多次实跑联调（2026-08-17） |
| 文档 | 见 `README.md` 与 `docs/` 其余三份 |

---

## 1. AI 辅助使用说明

| 问项 | 回答 |
|---|---|
| 使用了什么 AI | **Claude**（Anthropic 出品；本工程使用 Claude Code CLI 接入） |
| 什么平台 | **Claude Code**，运行于 **本地终端**（Linux，Ubuntu 22.04） |
| 用途 | ①生成 ROS 2 包骨架与 launch/config 文件；②编写一键脚本与对比分析工具（Python）；③整理中文文档（README / docs）；④排错与命令执行 |
| 人机分工 | AI 负责代码/脚本/文档初稿与排错建议；**关键操作（建图遥控、保存地图、导航演示）与全部仿真运行由使用者人工执行**；AI 生成内容经人工审阅后集成 |

> 说明：使用 AI 仅作为编码与文档辅助工具，所有仿真效果（建图质量、导航表现）均来自
> 人工遥控实跑的真实数据，未使用 AI 生成或伪造任何运行结果。



## 2. 关键失败案例（含真实终端报错）

> 每个案例：现象（真实报错原文）→ 原因 → 修复。这些是排查过程的真实记录。

### 2.1 conda Python 抢占 PATH 导致 `lxml` 缺失

**现象**：启动仿真 spawn 机器人时，`spawn_entity.py`（`#!/usr/bin/env python3`）报：

```text
ModuleNotFoundError: No module named 'lxml'
```

**原因**：本机终端里 conda 的 python3（3.14）排在 PATH 最前，缺少 rclpy/lxml；而系统
`/usr/bin/python3`（3.10）两者齐全。

**修复**：所有脚本/launch 统一在解释前 `export PATH=/usr/bin:/bin:$PATH`，把系统 python 放最前。

### 2.2 colcon 构建 `install(PROGRAMS ...)` 通配符失败

**现象**：

```text
Error: glob 'launch/*.launch.py' 无法匹配，安装失败
```

**原因**：CMake 的 `install(PROGRAMS ...)` 不做 glob 展开，`launch/*.launch.py` 不会被展开。

**修复**：6 个包统一改用 `install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})`。

### 2.3 launch 引用文件名与磁盘文件名不一致

**现象**：`robot_world.launch.py` 引用 `spawn_robot.launch.py`，但磁盘上仍是换名前的旧文件名，
导致找不到 spawn 文件；同理 rviz 配置（旧命名 `.rviz` vs 实际 `robot_cartographer.rviz`）。

**原因**：全局换名时只改了内容引用、漏了文件重命名。

**修复**：`mv` 重命名 + 逐文件核对 launch 中的文件名引用。

### 2.4 换名残留：大小写与短名漏改

**现象**：模型 `model.config` 里仍残留大小写变体、SDF 里残留旧短名（换名前的前缀名）。

**原因**：`sed` 只匹配了小写/精确写法，未覆盖大小写与短名变体。

**修复**：`sed` 补全大小写与短名替换（含 `_imu` 等前缀变体），最后全局 `grep -ri <旧名关键字>` 复核为零。

### 2.5 nav2 参数文件版本不匹配

**现象**：Navigation2 启动后部分节点缺 `use_sim_time`、行为异常。

**原因**：换名时拷入的是旧版 `burger.yaml`，缺少 Humble 分支所需参数。

**修复**：替换为官方 humble 版 `burger.yaml` 内容（`robot.yaml` + `param/humble/robot.yaml`）。



## 3. 实测与验证记录

### 3.1 传感器 / 话题自测（M4）

```text
ros2 topic hz /scan   → 约 5.0 Hz
ros2 topic hz /odom   → 约 30 Hz
tf2_echo base_footprint base_scan  → 偏移约 [-0.032, 0.000, 0.182]
```

### 3.2 两次建图结果（M5 / M6，`maps/`）

| 地图 | 尺寸 | 占用 | 空白 | 未知 | 连通分量 |
|---|---|---|---|---|---|
| `robot_cartographer.pgm` | 124×116 | 745（5.18%） | 7867（54.69%） | 5772（40.13%） | 11 |
| `robot_slam_toolbox.pgm` | 112×103 | 784（6.80%） | 7840（67.96%） | 2912（25.24%） | 12 |

### 3.3 对比分析结论（详见 `SLAM_Comparison.md`）

| 维度 | Cartographer | SLAM Toolbox | 结论 |
|---|---|---|---|
| 覆盖完整度（未知率） | 40.13% | **25.24%** | 方法二覆盖更全 |
| 圆柱定位 RMSE | **0.027m** | 0.043m | 方法一定位更准 |
| 与理想世界 IoU / Precision | **0.116 / 0.642** | 0.115 / 0.611 | 基本持平 |
| 两图一致性 IoU | 0.305（召回 0.61） | | 重复性好 |

---

## 4. 素材归档清单

> 原则：只保留有实际意义、可复核的材料。

| 类别 | 位置 | 说明 |
|---|---|---|
| 地图产物（PGM/YAML/PNG） | `maps/` | 两次建图原始数据 + 可视化图片 |
| RViz/地图可视化 | `maps/*.png` | 已生成，可直接用于报告 |
| 运行截图（Gazebo/RViz） | `docs/screenshots/` | **待使用者补充**（建图过程、导航过程） |
| 终端报错日志 | `scripts/logs/` | `07_measure_resources.sh` 采集的 CPU/内存日志 |
| 资源占用数据 | `docs/SLAM_Comparison.md` §2.2 | 待 `07` 脚本补填 |
| 演示视频 | 使用者自录（不随源码上交） | 按 `Operation_Manual.md` §11 流程 |

---

## 5. 遗留事项

- [ ] `docs/screenshots/` 补充 Gazebo 与 RViz 实拍截图（建议：建图实时画面、两地图对比、导航到位画面）
- [ ] 运行 `07_measure_resources.sh` 采集两 SLAM 的 CPU/内存，填入 `SLAM_Comparison.md` §2.2
- [ ] 录制演示视频（按操作手册 §11 流程）
