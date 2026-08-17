#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 map_saver 保存的地图 (.pgm) 的占用/空白/未知像素，用于双 SLAM 对比。

用法：
    python3 scripts/analyze_map.py maps/robot_cartographer.pgm [more.pgm ...]

输出每张地图：分辨率、像素尺寸、占用/空白/未知占比、占用率、墙连通分量数（粗略）。
"""
import struct
import sys


def read_pgm(path):
    """读取 P5（二进制）或 P2（ASCII）PGM，返回 (width, height, pixels[row][col])，pixels 0~255。"""
    with open(path, "rb") as f:
        data = f.read()
    # 解析 PGM 头（跳过空白与 # 注释行）
    tokens = []
    i = 0
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
    magic, width, height, maxval = tokens[0], int(tokens[1]), int(tokens[2]), int(tokens[3])
    if magic not in ("P5", "P2"):
        raise ValueError(f"仅支持 P5/P2，得到 {magic}")
    width, height = int(width), int(height)
    if magic == "P5":
        px = list(data[i:i + width * height])
    else:
        px = [int(x) for x in data[i:].split()[: width * height]]
    if len(px) < width * height:
        raise ValueError(f"像素数不足: {len(px)} < {width * height}")
    return width, height, px


def flood_fill_count(occ, w, h):
    """对占用像素做 4 邻接连通分量计数（粗略衡量墙体块数）。"""
    seen = [False] * (w * h)
    count = 0
    stack = []
    for start in range(w * h):
        if occ[start] and not seen[start]:
            count += 1
            stack.append(start)
            seen[start] = True
            while stack:
                p = stack.pop()
                x, y = p % w, p // w
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        q = ny * w + nx
                        if occ[q] and not seen[q]:
                            seen[q] = True
                            stack.append(q)
    return count


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    for path in sys.argv[1:]:
        w, h, px = read_pgm(path)
        # map_saver 约定：0=占用(黑) 254=空白(白) 205=未知(灰)
        occ = sum(1 for v in px if v <= 100)
        free = sum(1 for v in px if v >= 240)
        unknown = w * h - occ - free
        ratio = lambda n: n / (w * h) * 100.0
        occ_flag = [v <= 100 for v in px]
        comps = flood_fill_count(occ_flag, w, h)
        print(f"{path}")
        print(f"  尺寸 {w}x{h}  ({w*h} 栅格)")
        print(f"  占用 {occ} ({ratio(occ):.2f}%) | 空白 {free} ({ratio(free):.2f}%) | 未知 {unknown} ({ratio(unknown):.2f}%)")
        print(f"  占用率(占用/全部) = {ratio(occ):.2f}%   墙连通分量数 ≈ {comps}")
        print()


if __name__ == "__main__":
    main()
