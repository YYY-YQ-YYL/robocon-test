#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 map_saver 的 .pgm 地图转成可视化 PNG 图片。

用法：
    python3 scripts/map_to_png.py maps/robot_cartographer.pgm [maps/robot_slam_toolbox.pgm ...]

约定（map_saver）：0=占用(黑)，205=未知(灰)，254=空白(白)。
输出同名 .png（无边框、真实比例）。
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install pillow（本机 /usr/bin/python3 已装）")


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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for path in sys.argv[1:]:
        w, h, px = read_pgm(path)
        img = Image.new("L", (w, h))
        img.putdata(px)          # 灰度直接映射：0=黑(占用)、205=灰(未知)、254=白(空白)
        # 转 RGB 并放大 6 倍，方便直接查看/粘贴到报告
        rgb = img.convert("RGB").resize((w * 6, h * 6), Image.NEAREST)
        out = os.path.splitext(path)[0] + ".png"
        rgb.save(out)
        print(f"已生成 {out}  ({w*6}x{h*6})  →  RGB: 0=占用(黑) 205=未知(灰) 254=空白(白)")


if __name__ == "__main__":
    main()
