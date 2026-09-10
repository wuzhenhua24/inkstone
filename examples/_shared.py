# -*- coding: utf-8 -*-
"""examples/ 共用：读 data/ 下的 CSV，出图到 out/。

三个例子都不联网。数据在 examples/data/*.csv 里，要更新就跑
`python3 examples/fetch.py` 重抓——渲染这一步必须离线且确定性，
否则同一份代码今天和明天出的图不一样，README 里的样张也就没法信。
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from scripts.render import render          # noqa: E402


def rows(name):
    """读一份数据表。第一行是 `# 来源…`，跳过后按标准 CSV 解析——
    国名里有逗号（Korea, Rep.），手工 split 会当场错位。"""
    path = os.path.join(HERE, "data", name)
    with open(path, encoding="utf-8") as f:
        first = f.readline()
        assert first.startswith("#"), f"{name} 少了来源行"
        return list(csv.DictReader(f)), first.lstrip("# ").strip()


def emit(svg, stem):
    made = render(svg, stem)
    print(f"  {stem}  ->  {', '.join(os.path.basename(m) for m in made)}")
    return made
