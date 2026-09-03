# -*- coding: utf-8 -*-
"""渲染全部图型的演示样张。数据确定性，每次跑出来必须长一样。"""
import sys, os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from charts.rank_bars import rank_bars
from charts.day_series import day_series
from charts.hundred_grid import hundred_grid
from charts.beeswarm import beeswarm
from charts.matrix_heat import matrix_heat
from charts.tick_box import tick_box
from charts.line_family import line_family
from charts._data import rnd
from scripts.render import render

# ── R1 定序条 ────────────────────────────────────────────────
render(rank_bars(
    [("企业微信", 3820), ("钉钉", 3140), ("飞书", 2260),
     ("Teams", 1180), ("Slack", 640), ("其他", 310)],
    title="协同工具装机量，企业微信仍领先一个身位",
    subtitle="按活跃企业数排序 · 单位：千家 · 2026 年 Q2",
    source="数据来源：内部装机统计 · N=11,350",
    column="single",
), "r1-rank-bars")

# ── S1 日序条码 ──────────────────────────────────────────────
start = date(2026, 4, 1)
series = []
for i in range(91):
    d = start + timedelta(days=i)
    v = 520 + 180 * rnd(i, 1)
    if d.weekday() >= 5:
        v *= 0.55
    if i in (23, 24, 25):
        v *= 2.1
    series.append((d, round(v)))

render(day_series(
    series,
    title="日活在 4 月下旬的活动后回到基线，未形成留存",
    subtitle="每日活跃企业数 · 单位：家 · 2026-04-01 至 2026-06-30",
    source="数据来源：服务端埋点 · 口径含试用账号",
    column="double", annotate_top=3,
), "s1-day-series")

# ── C1 百格方阵 ──────────────────────────────────────────────
render(hundred_grid(
    [("自然搜索", 3120), ("老客推荐", 2260), ("内容投放", 1840),
     ("线下活动", 1180), ("渠道分销", 640), ("其他", 310)],
    title="新签客户里三成来自自然搜索，投放只占两成",
    subtitle="按新签合同数构成 · 一格 = 1% · 2026 年 H1",
    source="数据来源：CRM 首次归因 · N=9,350",
    column="single",
), "c1-hundred-grid")

# ── D2 蜂群 ──────────────────────────────────────────────────
SPEC = [("旗舰版", 34, 180, 90), ("专业版", 46, 95, 55),
        ("标准版", 52, 48, 30), ("入门版", 38, 22, 14)]
swarm = []
for gi, (name, cnt, center, spread) in enumerate(SPEC):
    vs = []
    for i in range(cnt):
        v = center + spread * (rnd(i, gi + 7) - 0.42) * 2
        if rnd(i, gi + 30) > 0.93:
            v *= 1.9
        vs.append(round(max(4, v)))
    swarm.append((name, vs))

render(beeswarm(
    swarm,
    title="标准版成交额集中，旗舰版靠少数大单撑起中位数",
    subtitle="逐笔成交金额 · 一个点 = 一笔合同 · 单位：万元 · 2026 H1",
    source="数据来源：CRM 成交记录 · N=170",
    column="double",
), "d2-beeswarm")

# ── M1 矩阵热力 ──────────────────────────────────────────────
ROWS = ["华东", "华南", "华北", "西南", "华中", "东北"]
COLS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"]
VALUES = [[round(30 + 90 * rnd(i * 13 + j, 5) * (1.5 - i * 0.13) + j * 4)
           for j in range(len(COLS))] for i in range(len(ROWS))]
VALUES[0][6], VALUES[0][7] = 214, 198

render(matrix_heat(
    ROWS, COLS, VALUES,
    title="华东在 7 月拉开差距，东北全年未起量",
    subtitle="分区域月度新签合同数 · 一格 = 一个区域月 · 单位：份 · 2026 年",
    source="数据来源：CRM 合同台账 · N=4,120",
    column="double",
), "m1-matrix-heat")

# ── D3 五数摘要 ──────────────────────────────────────────────
BOX = [("华东", 60, 4.2, 1.6), ("华南", 55, 5.1, 1.4), ("华北", 48, 6.8, 2.2),
       ("西南", 44, 7.5, 1.9), ("华中", 40, 6.1, 1.7), ("东北", 36, 9.2, 2.8)]
boxes = []
for gi, (name, cnt, center, spread) in enumerate(BOX):
    vs = []
    for i in range(cnt):
        v = center + spread * (rnd(i, gi + 11) - 0.45) * 2
        if rnd(i, gi + 55) > 0.94:
            v += spread * 4.5
        vs.append(round(max(0.4, v), 1))
    boxes.append((name, vs))

render(tick_box(
    boxes,
    title="东北的工单响应时长中位数最高，且拖尾最重",
    subtitle="首次响应时长分位数 · 箱=四分位距 · 点=异常值 · 单位：小时",
    source="数据来源：工单系统 · N=283 · 异常值按 1.5 IQR 判定",
    column="single",
), "d3-tick-box")

# ── S2 细线族 ────────────────────────────────────────────────
LINE = [("企业微信", 62, 4.6), ("钉钉", 58, 2.1), ("飞书", 40, 5.2),
        ("Teams", 34, 1.1), ("Slack", 26, -0.9)]
lines = []
for si, (name, start, slope) in enumerate(LINE):
    vs, v = [], start
    for i in range(12):
        v += slope + 6 * (rnd(i, si + 3) - 0.5)
        vs.append(round(max(4, v), 1))
    lines.append((name, vs))

render(line_family(
    lines, [f"{m}月" for m in range(1, 13)],
    title="飞书全年增速最快，Slack 是唯一下滑的",
    subtitle="月度活跃企业数 · 单位：千家 · 2026 年",
    source="数据来源：内部装机统计",
    column="double",
), "s2-line-family")

print("已渲染 7 张，产物在 out/")
