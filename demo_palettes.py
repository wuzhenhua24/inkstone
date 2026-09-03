# -*- coding: utf-8 -*-
"""彩色档样张。每套色板一张，用于目视核对和灰度等价测试。"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens as T
import palettes
from charts.rank_bars import rank_bars
from charts.matrix_heat import matrix_heat
from charts._data import rnd
from scripts.render import render

DATA = [("企业微信", 3820), ("钉钉", 3140), ("飞书", 2260),
        ("Teams", 1180), ("Slack", 640), ("其他", 310)]
ROWS = ["华东", "华南", "华北", "西南"]
COLS = [f"{m}月" for m in range(1, 9)]
HEAT = [[round(30 + 90 * rnd(i * 13 + j, 5) * (1.5 - i * .13) + j * 4)
         for j in range(8)] for i in range(4)]


def render_all(name):
    cn = palettes.PRESETS[name]["cn"]
    with T.use(name):
        render(rank_bars(
            DATA, title="协同工具装机量，企业微信仍领先一个身位",
            subtitle=f"按活跃企业数排序 · 单位：千家 · 色板 {cn}",
            source="数据来源：内部装机统计", column="single",
        ), f"pal-{name}-rank")
        render(matrix_heat(
            ROWS, COLS, HEAT, title="分区域月度新签合同数",
            subtitle=f"格内数字在深底上翻成纸白 · 单位：份 · 色板 {cn}",
            source="数据来源：CRM 合同台账", column="double",
        ), f"pal-{name}-heat")


if __name__ == "__main__":
    for n in palettes.PRESETS:
        render_all(n)
    print(f"已渲染 {len(palettes.PRESETS)} 套色板 × 2 张")
