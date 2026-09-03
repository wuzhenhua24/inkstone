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
from charts.small_multiples import small_multiples
from charts.diverging_bars import diverging_bars
from charts.dot_cascade import dot_cascade
from charts.stacked_bands import stacked_bands
from charts.step_histogram import step_histogram
from charts.scatter_fit import scatter_fit
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

# ── S3 小倍数网格 ────────────────────────────────────────────
GRID = [("华东", 88, 3.4), ("华南", 74, 2.2), ("华北", 66, 1.1), ("西南", 58, 2.8),
        ("华中", 52, 0.6), ("东北", 41, -1.2), ("西北", 33, 1.6), ("港澳台", 24, 0.4)]
grid = []
for si, (name, start, slope) in enumerate(GRID):
    vs, v = [], start
    for i in range(12):
        v += slope + 7 * (rnd(i, si + 17) - 0.5)
        vs.append(round(max(3, v), 1))
    grid.append((name, vs))

render(small_multiples(
    grid, [f"{m}月" for m in range(1, 13)],
    title="八个区域里只有东北全年走低",
    subtitle="月度新签合同数 · 单位：份 · 2026 年",
    source="数据来源：CRM 合同台账",
    column="double",
), "s3-small-multiples")

# ── R2 分岔条 ────────────────────────────────────────────────
render(diverging_bars(
    [("自然搜索", 412), ("老客推荐", 268), ("内容投放", 96), ("线下活动", -58),
     ("渠道分销", -184), ("电话外呼", -327)],
    title="投放和推荐仍在净增，外呼流失最重",
    subtitle="新签减去流失的净变化 · 单位：家 · 2026 H1 对比 H2",
    source="数据来源：CRM 首次归因",
    column="single",
), "r2-diverging-bars")

# ── R3 点阵瀑布 ──────────────────────────────────────────────
render(dot_cascade(
    [("登录失败", 1840), ("同步超时", 1260), ("附件上传失败", 910),
     ("消息重复", 620), ("权限校验错误", 430), ("导出为空", 180)],
    title="登录失败占了故障工单的三分之一",
    subtitle="按故障类型统计的工单量 · 2026 H1",
    source="数据来源：工单系统",
    column="single", unit="件",
), "r3-dot-cascade")

# ── C2 堆叠带 ────────────────────────────────────────────────
BAND_SPEC = [("自然搜索", 42, 1.9), ("老客推荐", 30, 1.2), ("内容投放", 20, 1.6),
             ("渠道分销", 11, 0.2), ("线下活动", 5, 0.05)]
band_layers = []
for si, (name, start, slope) in enumerate(BAND_SPEC):
    vs, v = [], start
    for i in range(12):
        v = max(1, v + slope + 3 * (rnd(i, si + 23) - 0.5))
        vs.append(round(v, 1))
    band_layers.append((name, vs))

render(stacked_bands(
    band_layers, [f"{m}月" for m in range(1, 13)],
    title="总量全年增长，但增量几乎都来自自然搜索和内容投放",
    subtitle="月度新签合同数构成 · 单位：份 · 2026 年",
    source="数据来源：CRM 首次归因",
    column="double",
), "c2-stacked-bands")

# ── D1 阶梯直方 ──────────────────────────────────────────────
hist_vals = []
for i in range(240):
    v = 18 + 26 * (rnd(i, 41) + rnd(i, 42) + rnd(i, 43)) / 3
    if rnd(i, 44) > 0.9:
        v += 22
    hist_vals.append(round(v, 1))

render(step_histogram(
    hist_vals,
    title="多数账号在 25–40 分钟内完成首次配置",
    subtitle="首次配置耗时分布 · 单位：分钟",
    source="数据来源：引导流程埋点",
    column="single", unit="分钟",
), "d1-step-histogram")

# ── M2 散点带回归 ────────────────────────────────────────────
pts = []
for i in range(86):
    x = 4 + 30 * rnd(i, 61)
    y = 12 + 2.1 * x + 26 * (rnd(i, 62) - 0.5)
    pts.append((round(x, 1), round(max(3, y), 1)))

render(scatter_fit(
    pts,
    title="接入的应用越多，月活跃天数越高",
    subtitle="每点 = 一个企业账号 · 2026 H1",
    source="数据来源：服务端埋点",
    column="single", x_name="已接入应用数", y_name="月活跃天数",
), "m2-scatter-fit")

print("已渲染 13 张，产物在 out/")
