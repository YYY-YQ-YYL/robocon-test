#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双 SLAM 地图 vs 理想世界 + 两图一致性对比（IoU / Precision / Recall of occupied）。

背景：两张地图由两次独立的 SLAM 会话保存。每次会话的 map 帧都锚定在机器人出生点，
但各自会话中 map→odom 会因回环修正发生漂移，所以两张图的坐标系并不相同，也未必
与世界坐标重合。因此不能用"按像素对齐"直接算 IoU（必然≈0）。

本脚本采用**刚性配准**（先粗后细：FFT 交叉相关求最优平移，再搜索最优旋转角）：
  1) 每张地图的占用格 → 在世界坐标网格上做刚体变换 (θ, tx, ty)，
     使其与"按世界设计坐标生成的理想地图"重合，报告对齐后的 IoU/Precision/Recall
     （即该地图能解释理想障碍的程度，两图在完全相同的理想参考下对比，公平）；
  2) 两张地图互相配准（以方法一为参考），报告两图占用格的一致性 IoU；
  3) 同时输出每张图恢复出的 map→世界 变换，便于核对出生点锚定是否合理。

理想世界几何（与 robot_gazebo/models/robot_world/model.sdf 一致）：
  · 9 根圆柱：r=0.15m、高 0.5m，中心位于 (x,y) ∈ {-1.1, 0, 1.1}²
  · 中心墙 wall.dae：单位英寸、scale 0.25、yaw=-90°，占地约 1.3m × 5.7m、
    中心 (0,0)（面板稀疏，此处按其占地矩形近似）
  · 5 个六边形地面地标：贴图式、2D 激光不可见，不纳入理想地图

用法：
    python3 scripts/compare_maps.py maps/robot_cartographer.yaml maps/robot_slam_toolbox.yaml
    python3 scripts/compare_maps.py maps/robot_cartographer.yaml          # 仅单图 vs 理想
"""
import math
import os
import sys

import numpy as np

RES = 0.05          # 世界网格分辨率（与地图一致）
GRID = 440          # 网格尺寸（22m / 0.05 = 440），居中放置防 FFT 循环卷积卷绕
OFFSET = 11.0       # 网格 cell(0,0) → 世界坐标 (-11, -11)

# ---------------------------------------------------------------------------
# 世界障碍设计几何（单位米）
# ---------------------------------------------------------------------------
OBSTACLES = []

for gx in (-1.1, 0.0, 1.1):
    for gy in (-1.1, 0.0, 1.1):
        OBSTACLES.append(("cyl", gx, gy, 0.15))

# 中心墙：wall.dae（英寸、scale 0.25、yaw=-90°）。两张 SLAM 地图共识显示其为
# 世界中央约 5.6m × 5.2m 的薄壁轮廓结构（两侧立板 + 上下横档，中部空心），
# 故理想模型按同尺寸薄环近似："ring" = 外矩形减内矩形，壁厚 0.3m。
OBSTACLES.append(("ring", 0.0, 0.0, 5.60, 5.20, 0.30))   # 中心墙薄环近似


# ---------------------------------------------------------------------------
# PGM / YAML 读取
# ---------------------------------------------------------------------------
def read_pgm(path):
    with open(path, "rb") as f:
        data = f.read()
    tokens, i = [], 0
    while len(tokens) < 4:
        while i < len(data) and data[i:i + 1] in b" \t\n\r":
            i += 1
        if i < len(data) and data[i:i + 1] == b"#":
            while i < len(data) and data[i:i + 1] != b"\n":
                i += 1
            continue
        start = i
        while i < len(data) and data[i:i + 1] not in b" \t\n\r":
            i += 1
        tokens.append(data[start:i].decode())
    while i < len(data) and data[i:i + 1] in b" \t\n\r":
        i += 1
    magic, w, h, maxval = tokens[0], int(tokens[1]), int(tokens[2]), int(tokens[3])
    if magic != "P5":
        raise ValueError(f"仅支持 P5，得到 {magic}")
    px = list(data[i:i + w * h])
    if len(px) < w * h:
        raise ValueError(f"像素数不足: {len(px)} < {w*h}")
    return w, h, px


def read_map_yaml(path):
    meta = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    image = meta["image"].strip('"')
    res = float(meta["resolution"])
    ox, oy, yaw = [float(x) for x in meta["origin"].strip("[]").split(",")]
    return image, res, ox, oy, yaw


# ---------------------------------------------------------------------------
# 理想世界
# ---------------------------------------------------------------------------
def world_to_cell(wx, wy):
    """世界坐标 (m) → 网格 (col, row)。"""
    return int(round((wx + OFFSET) / RES)), int(round((wy + OFFSET) / RES))


def rasterize_ideal_cells(dilation=1):
    """理想占用格集合（世界网格坐标）。dilation：向外膨胀格数，容忍地图障碍带更粗。"""
    cells = set()
    for kind, cx, cy, *rest in OBSTACLES:
        if kind == "cyl":
            r = rest[0]
            ccx, ccy = world_to_cell(cx, cy)
            rr = int(math.ceil(r / RES))
            for gx in range(ccx - rr, ccx + rr + 1):
                for gy in range(ccy - rr, ccy + rr + 1):
                    if (gx - ccx) ** 2 + (gy - ccy) ** 2 <= rr ** 2:
                        cells.add((gx, gy))
        elif kind == "box":
            sx, sy = rest
            x0, y0 = world_to_cell(cx - sx / 2, cy - sy / 2)
            x1, y1 = world_to_cell(cx + sx / 2, cy + sy / 2)
            for gx in range(x0, x1 + 1):
                for gy in range(y0, y1 + 1):
                    cells.add((gx, gy))
        elif kind == "ring":
            sx, sy, t = rest              # 外矩形 (sx×sy) 减内矩形，壁厚 t
            x0, y0 = world_to_cell(cx - sx / 2, cy - sy / 2)
            x1, y1 = world_to_cell(cx + sx / 2, cy + sy / 2)
            ix0, iy0 = world_to_cell(cx - (sx / 2 - t), cy - (sy / 2 - t))
            ix1, iy1 = world_to_cell(cx + (sx / 2 - t), cy + (sy / 2 - t))
            for gx in range(x0, x1 + 1):
                for gy in range(y0, y1 + 1):
                    if not (ix0 <= gx <= ix1 and iy0 <= gy <= iy1):
                        cells.add((gx, gy))
    if dilation > 0:
        cells = set(c for x, y in cells
                    for dx in range(-dilation, dilation + 1)
                    for dy in range(-dilation, dilation + 1)
                    for c in [(x + dx, y + dy)])
    return cells


# ---------------------------------------------------------------------------
# 配准
# ---------------------------------------------------------------------------
def grid_from_cells(cells, shape=(GRID, GRID)):
    arr = np.zeros(shape, dtype=np.float64)
    for x, y in cells:
        if 0 <= x < shape[0] and 0 <= y < shape[1]:
            arr[y, x] = 1.0
    return arr


def map_cells_in_map_frame(occ, w, h, res, ox, oy):
    """占用像素 → map 帧坐标（米）。返回 list[(mx,my)]。"""
    pts = []
    for row in range(h):
        my = oy + (h - 1 - row + 0.5) * res
        base = row * w
        for col in range(w):
            if occ[base + col]:
                pts.append((ox + (col + 0.5) * res, my))
    return pts


def rotate(pts, deg):
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def best_translation_grid(pts, ideal_arr):
    """对已旋转的点集，用 FFT 交叉相关求最佳平移。返回 (du, dv) 网格位移与重叠数。

    FFT 相关是"环形"相关，负位移会卷绕到网格另一端（> GRID/2），这里解卷绕为带符号位移。
    """
    B = grid_from_cells({world_to_cell(x, y) for x, y in pts})
    B_fft = np.fft.fft2(B)
    corr = np.fft.ifft2(np.fft.fft2(ideal_arr) * np.conj(B_fft)).real
    v, u = np.unravel_index(corr.argmax(), corr.shape)   # 数组是 [row=y][col=x]
    if u > GRID / 2:
        u -= GRID
    if v > GRID / 2:
        v -= GRID
    return u, v, int(round(corr[(v + GRID) % GRID, (u + GRID) % GRID]))


def overlap_after_shift(pts, du, dv, ideal_set):
    """平移 (du,dv) 后与理想集的重叠格数。"""
    n = 0
    for x, y in pts:
        gx, gy = world_to_cell(x, y)
        if (gx + du, gy + dv) in ideal_set:
            n += 1
    return n


def metrics(pts, du, dv, ideal_set):
    """对齐后 IoU / Precision / Recall of occupied（世界网格格数）。"""
    b_cells = set()
    for x, y in pts:
        gx, gy = world_to_cell(x, y)
        b_cells.add((gx + du, gy + dv))
    inter = len(b_cells & ideal_set)
    union = len(b_cells | ideal_set)
    iou = inter / union if union else 0.0
    prec = inter / len(b_cells) if b_cells else 0.0
    rec = inter / len(ideal_set) if ideal_set else 0.0
    return iou, prec, rec, inter, len(b_cells), len(ideal_set)


def register(pts, ideal_set, ideal_arr, label, deg_range=(-20, 20), deg_step=1.0):
    """搜索最优刚体变换 (deg, du, dv)，返回 (iou, prec, rec, best)。"""
    best = None  # (overlap, deg, du, dv)
    for deg in [d / 10 for d in range(deg_range[0] * 10, deg_range[1] * 10 + 1, int(deg_step * 10))]:
        rp = rotate(pts, deg)
        du, dv, ov = best_translation_grid(rp, ideal_arr)
        if best is None or ov > best[0]:
            best = (ov, deg, du, dv)
    # 细调：围绕粗解在 ±2°、±6 格内精化
    _, bd, bu, bv = best
    for deg in [d / 10 for d in range(int((bd - 2) * 10), int((bd + 2) * 10) + 1, 1)]:
        rp = rotate(pts, deg)
        for du in range(bu - 3, bu + 4):
            for dv in range(bv - 3, bv + 4):
                ov = overlap_after_shift(rp, du, dv, ideal_set)
                if best is None or ov > best[0]:
                    best = (ov, deg, du, dv)
    _, bd, bu, bv = best
    iou, prec, rec, inter, nb, nideal = metrics(rotate(pts, bd), bu, bv, ideal_set)
    print(f"  [{label}] 配准 (θ={bd:.1f}°, map→世界平移≈({bu*RES:+.2f},{bv*RES:+.2f})m)  "
          f"IoU={iou:.3f}  Precision={prec:.3f}  Recall={rec:.3f}")
    print(f"           占用格: 地图={nb}, 理想={nideal}, 交集={inter}")
    return iou, prec, rec, (bd, bu, bv)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ideal_set = rasterize_ideal_cells(dilation=1)
    ideal_arr = grid_from_cells(ideal_set)

    maps = []
    for y in sys.argv[1:]:
        image, res, ox, oy, yaw = read_map_yaml(y)
        image = image if os.path.isabs(image) else os.path.join(os.path.dirname(y), os.path.basename(image))
        w, h, px = read_pgm(image)
        occ = [v <= 150 for v in px]              # 占用掩码：0=黑=占用，205=未知，254=空白
        pts = map_cells_in_map_frame(occ, w, h, res, ox, oy)
        maps.append((os.path.basename(y), pts, res, ox, oy, yaw))
        print(f"加载 {os.path.basename(y)}: {w}x{h} 占用格 {sum(occ)}")

    print(f"\n=== 各 SLAM 地图 vs 理想世界（刚性配准后） ===")
    print(f"  理想：9 圆柱(r=0.15) + 中心墙(5.6×5.2m 薄环近似)；六边形地标不可见不建模。")
    print(f"  配准：搜索 θ∈[-20°,20°]、平移经 FFT 交叉相关求出，两图用同一理想参考，可比。\n")
    results = []
    for name, pts, res, ox, oy, yaw in maps:
        if abs(yaw) > 0.01:
            print(f"  注意: {name} 地图带 yaw={yaw:.3f} 旋转（map_saver 一般写 0）")
        r = register(pts, ideal_set, ideal_arr, label=f"{name} vs 理想")
        results.append((name, r))

    if len(maps) >= 2:
        print(f"\n=== 两张 SLAM 地图之间的一致性（以 {maps[0][0]} 为参考配准） ===")
        ref_name, ref_pts, *_ = maps[0]
        for name, pts, *_ in maps[1:]:
            # 参考图当作理想：栅格化后配准
            ref_set = set()
            for x, y in ref_pts:
                gx, gy = world_to_cell(x, y)
                ref_set.add((gx, gy))
            ref_arr = grid_from_cells(ref_set)
            register(pts, ref_set, ref_arr, label=f"{name} vs {ref_name}",
                     deg_range=(-8, 8), deg_step=0.5)
    print()


if __name__ == "__main__":
    main()
