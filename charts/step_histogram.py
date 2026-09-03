# -*- coding: utf-8 -*-
"""D1 阶梯直方 · 单变量连续分布"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import histogram, median, nice_ticks, fmt, decimals_for


# ════ D1 阶梯直方 ════
# 数据形状：单变量连续分布，只看整体形状，不分组
# 版心：single / a4body
# 失效：要按组比较 → D2 蜂群 / D3 五数摘要；样本 <30 → 直接列点
def step_histogram(values, title=None, subtitle=None, source=None,
                   column="single", unit="", bins=None, show_median=True):
    """values: [数值, ...]"""
    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]

    edges, counts = histogram(values, bins)
    cmax = max(counts) or 1
    yt = nice_ticks(0, cmax, 4)
    ymax = yt[-1]

    px0 = x0 + max(S.text_width(f"{t:,g}", T.SIZE["label"]) for t in yt) + 4
    plot_h = 74.0
    top = S.head_height(title, subtitle, W)
    base = top + plot_h
    bw = (x1 - px0) / len(counts)

    parts = []
    for t in yt:
        gy = base - plot_h * t / ymax
        parts.append(S.line(px0, gy, x1, gy, T.GRAY[6], T.STROKE["hairline"]))
        parts.append(S.text(px0 - 4, gy + T.SIZE["label"] * 0.35, f"{t:,g}",
                            T.SIZE["label"], T.GRAY[3], anchor="end"))

    # 浅填充给出面积感，深阶梯线给出形状。只填充会糊，只画线会显得空。
    for k, c in enumerate(counts):
        h = plot_h * c / ymax
        parts.append(S.rect(px0 + k * bw, base - h, bw, h, T.GRAY[5]))

    pts = []
    for k, c in enumerate(counts):
        gy = base - plot_h * c / ymax
        pts += [f"{T.px(px0 + k * bw)} {T.px(gy)}",
                f"{T.px(px0 + (k + 1) * bw)} {T.px(gy)}"]
    parts.append(S.path("M" + " L".join(pts), T.GRAY[0], T.STROKE["data"]))

    if show_median:
        med = median(values)
        mx = px0 + (x1 - px0) * (med - edges[0]) / (edges[-1] - edges[0] or 1)
        parts.append(S.line(mx, top, mx, base, T.GRAY[0], T.STROKE["rule"], dash="2 2"))
        lab = f"中位数 {fmt(med, decimals_for([med]))}{unit}"
        lw = S.text_width(lab, T.SIZE["label"])
        parts.append(S.text(min(mx + 3, x1 - lw), top + T.SIZE["label"], lab,
                            T.SIZE["label"], T.GRAY[0]))

    parts.append(S.line(px0, base, x1, base, T.GRAY[3], T.STROKE["rule"]))
    dec = decimals_for(edges)
    step = max(1, -(-len(edges) // 7))     # 箱边太密就抽稀，绝不缩字号
    for k, e in enumerate(edges):
        if k % step:
            continue
        parts.append(S.text(px0 + k * bw, base + 3 + T.SIZE["label"], fmt(e, dec),
                            T.SIZE["label"], T.GRAY[3], anchor="middle"))

    note = (f"n={len(values)} · 箱宽 {fmt(edges[1] - edges[0], dec)}{unit} · "
            f"{len(counts)} 箱")
    src = f"{source} · {note}" if source else note
    H = base + T.SIZE["label"] + 8 + T.GAP["plot_source"] + T.SIZE["source"]
    return S.canvas(W, H, "\n".join(parts), title, subtitle, src)
