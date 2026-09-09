# -*- coding: utf-8 -*-
"""版心覆盖用的确定性样本数据。

demo.py 只跑 single 和 double 两档，`tokens.COLUMN` 却有五档——
onehalf / a4body / slide 三档长期处于「从没渲染过」的状态。
这里给每张图一份规模合规的样本，让测试能把 13 × 5 全部跑一遍。

数据量刻意压在各图型的上限之内（R1 窄栏 ≤8、D2 ≤180 点、C2 ≤5 层……），
这样跑出来的失败就一定是版心适配的问题，不是越界防护误伤。
"""
from datetime import date, timedelta

from charts._data import rnd
from charts.rank_bars import rank_bars
from charts.diverging_bars import diverging_bars
from charts.dot_cascade import dot_cascade
from charts.day_series import day_series
from charts.line_family import line_family
from charts.small_multiples import small_multiples
from charts.hundred_grid import hundred_grid
from charts.stacked_bands import stacked_bands
from charts.step_histogram import step_histogram
from charts.beeswarm import beeswarm
from charts.tick_box import tick_box
from charts.matrix_heat import matrix_heat
from charts.scatter_fit import scatter_fit

KW = dict(title="标题写结论不写图型名，且长到足以触发折行",
          subtitle="统计口径 · 单位：千家 · 2026 年上半年",
          source="数据来源：内部统计 · N=1,200")

_CAT6 = [(f"类目{i}", 100 - i * 12) for i in range(6)]
_XL = [f"{m}月" for m in range(1, 13)]
_SER3 = [(f"线{i}", [round(50 + 8 * rnd(j, i), 1) for j in range(12)]) for i in range(3)]
_DAYS = [(date(2026, 4, 1) + timedelta(days=i), round(100 + 80 * rnd(i, 1)))
         for i in range(91)]
_SWARM = [(f"组{i}", [round(20 + 40 * rnd(j, i), 1) for j in range(30)]) for i in range(4)]
_HEAT = [[round(30 + 90 * rnd(i * 13 + j, 5)) for j in range(8)] for i in range(4)]
_HIST = [round(20 + 30 * rnd(i, 41), 1) for i in range(200)]
_PTS = [(round(4 + 30 * rnd(i, 61), 1),
         round(12 + 2.1 * (4 + 30 * rnd(i, 61)) + 26 * (rnd(i, 62) - .5), 1))
        for i in range(60)]

# (编号, 画图函数)。函数只收一个 column 参数，其余走 KW。
ALL = [
    ("R1", lambda c: rank_bars(_CAT6, column=c, **KW)),
    ("R2", lambda c: diverging_bars([(f"类{i}", 100 - i * 40) for i in range(5)],
                                    column=c, **KW)),
    ("R3", lambda c: dot_cascade(_CAT6, column=c, **KW)),
    ("S1", lambda c: day_series(_DAYS, column=c, **KW)),
    ("S2", lambda c: line_family(_SER3, _XL, column=c, **KW)),
    ("S3", lambda c: small_multiples(_SER3, _XL, column=c, **KW)),
    ("C1", lambda c: hundred_grid(_CAT6, column=c, **KW)),
    ("C2", lambda c: stacked_bands(_SER3, _XL, column=c, **KW)),
    ("D1", lambda c: step_histogram(_HIST, column=c, **KW)),
    ("D2", lambda c: beeswarm(_SWARM, column=c, **KW)),
    ("D3", lambda c: tick_box(_SWARM, column=c, **KW)),
    ("M1", lambda c: matrix_heat(["华东", "华南", "华北", "西南"],
                                 [f"{m}月" for m in range(1, 9)], _HEAT, column=c, **KW)),
    ("M2", lambda c: scatter_fit(_PTS, column=c, **KW)),
]

# 图形区高度按宽度推导的五张。其余图型的高度由条数 / 格数定，
# 那是正确行为——6 项的定序条就该是 6 行高，跟栏多宽没关系。
RESPONSIVE = {"S1", "S2", "C2", "D1", "M2"}
