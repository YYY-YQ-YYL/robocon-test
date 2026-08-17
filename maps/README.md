# 地图目录

本目录存放两次 SLAM 建图保存的地图（`map_saver_cli` 输出 `.pgm` + `.yaml`）。

| 文件名（建议）       | 来源方法                  | 保存命令 |
|---------------------|--------------------------|----------|
| `robot_cartographer.pgm/.yaml` | 方法一：Cartographer  | `./scripts/05_save_map.sh robot_cartographer` |
| `robot_slam_toolbox.pgm/.yaml` | 方法二：SLAM Toolbox | `./scripts/05_save_map.sh robot_slam_toolbox` |

**注意**：必须在对应 SLAM 节点存活时保存（`/map` 是 latched 话题）。

对比分析：
```bash
python3 scripts/analyze_map.py maps/robot_cartographer.pgm maps/robot_slam_toolbox.pgm
python3 scripts/compare_maps.py maps/robot_cartographer.yaml maps/robot_slam_toolbox.yaml
```
