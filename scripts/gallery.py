# -*- coding: utf-8 -*-
"""把选定的产物同步进 docs/gallery/，供 README 展示。

用法：python3 demo.py && python3 examples/ex1_population.py && …
      python3 scripts/gallery.py

**为什么要入库一份。** out/ 是 gitignore 的，而 README 要能在 GitHub 上
直接显示图——一个图表项目的橱窗里没有图，是最贵的一处空白。

**为什么展示用 PNG 而不是 SVG。** GitHub 能渲染仓库内的相对路径 SVG，
但本项目的 SVG 依赖系统 CJK 字体栈：访客机器缺字时逐字符 fallback 会让
中文宽度和版心的关系变形——正好把「按实测宽度留位」这个卖点演示成错的。
PNG@300dpi 已经栅格化，所见即落纸。

**为什么 SVG 也一并入库。** 防漂：SVG 是确定性的（跑两次字节一致），
所以可以拿「入库的这份 == 当场重跑出来的那份」当机器判定。图型一改而
画廊没更新，测试当场红。PNG 不做字节断言——它跨 librsvg 版本会变，
macOS 和 CI 的 runner 就不是同一个结果。
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "docs", "gallery")

# 画廊选图。改这里就改了 README 的橱窗；改完记得重跑本脚本。
PICKS = [
    "ex3-urbanization",
    "ex1-population",
    "ex2-life-expectancy",
    "m1-matrix-heat",
    "d2-beeswarm",
    "s3-small-multiples",
]


def sync():
    os.makedirs(DEST, exist_ok=True)
    keep = set()
    missing = []
    for stem in PICKS:
        for ext in ("svg", "png"):
            src = os.path.join(ROOT, "out", f"{stem}.{ext}")
            if not os.path.exists(src):
                missing.append(os.path.basename(src))
                continue
            shutil.copyfile(src, os.path.join(DEST, f"{stem}.{ext}"))
            keep.add(f"{stem}.{ext}")
    if missing:
        raise SystemExit(f"out/ 里缺这些产物，先跑 demo.py 和 examples/：{missing}")
    # 从 PICKS 里删掉的图，文件也要跟着走，否则画廊里会留下没人引用的孤儿
    for f in sorted(os.listdir(DEST)):
        if f.endswith((".svg", ".png")) and f not in keep:
            os.remove(os.path.join(DEST, f))
            print(f"  移除不再入选的 {f}")
    print(f"  docs/gallery/ 已同步 {len(PICKS)} 张")


if __name__ == "__main__":
    sync()
