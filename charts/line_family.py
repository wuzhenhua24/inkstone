# -*- coding: utf-8 -*-
"""S2 细线族 · 3–6 条序列同轴比较"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import nice_ticks

MAX_SERIES = 6


def _place_labels(want, min_gap, top, bottom):
    """线端标签防重叠：按目标位置排序后逐个下推，整体超界就整体上移。

    返回每个标签的最终 y，顺序与输入一致。
    """
    idx = sorted(range(len(want)), key=lambda i: want[i])
    ys = [0.0] * len(want)
    prev = top - min_gap
    for i in idx:
        y = max(want[i], prev + min_gap)
        ys[i] = y
        prev = y
    over = ys[idx[-1]] - bottom if idx else 0
    if over > 0:                       # 整体上移，但不越过上界
        shift = min(over, min(ys) - top)
        for i in range(len(ys)):
            ys[i] -= max(0, shift)
    return ys


# ════ S2 细线族 ════
# 数据形状：3–6 条同单位序列在同一坐标系下比较
# 版心：double（170mm）
# 失效：>6 条 → S3 小倍数网格；只有一条 → S1 日序条码
def line_family(series, x_labels, title=None, subtitle=None, source=None,
                column="double", unit="", y_from_zero=True):
    """series: [(名称, [数值, ...]), ...]，按重要性降序传入。第一条最重。"""
    if len(series) > MAX_SERIES:
        raise ValueError(
            f"S2 细线族最多 {MAX_SERIES} 条，收到 {len(series)} 条。"
            f"再多线会互相穿插，灰阶和线宽都排不开——改用 S3 小倍数网格。")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]

    # 直接在线端标名字，不做图例。图例要求读者在色块和线之间来回配对，
    # 灰阶图上尤其费劲；直接标注把「识别」这件事从灰阶上卸下来，
    # 灰阶于是可以专职表示重要性。
    #
    # 代价是标签和线同色，所以线的灰必须留在文字安全档（GRAY[0..3]）内。
    # 只有 4 档而最多 6 条线，不够用——差额由线宽补。
    lab_w = max(S.text_width(n, T.SIZE["label"]) for n, _ in series)
    px1 = x1 - lab_w - 7

    allv = [v for _, vs in series for v in vs]
    ticks = nice_ticks(0 if y_from_zero else min(allv), max(allv))
    dlo, dhi = ticks[0], ticks[-1]

    # y 轴刻度标签也要装订线。x0 是版心左界，不是图形区左界——
    # 两者混为一谈，标签就会从纸外开始画。
    px0 = x0 + max(S.text_width(f"{t:,g}", T.SIZE["label"]) for t in ticks) + 4

    plot_h = 108.0
    axis_h = T.SIZE["label"] + 8
    top = S.head_height(title, subtitle, W)
    base = top + plot_h

    n = len(x_labels)
    def sx(i):
        return px0 + (px1 - px0) * i / max(1, n - 1)
    def sy(v):
        return base - plot_h * (v - dlo) / (dhi - dlo or 1)

    parts = []
    for t in ticks:                       # 网格先画，线压在上面
        parts.append(S.line(px0, sy(t), px1, sy(t), T.GRAY[6], T.STROKE["hairline"]))
        parts.append(S.text(px0 - 4, sy(t) + T.SIZE["label"] * 0.35, f"{t:,g}",
                            T.SIZE["label"], T.GRAY[3], anchor="end"))

    # 灰只有 4 档，线宽补足到 6 条可分
    inks = [T.GRAY[min(i, T.TEXT_SAFE_MAX)] for i in range(len(series))]
    widths = [T.STROKE["data"] * w for w in (1.5, 1.15, 1.0, 1.0, 0.75, 0.75)]
    # 灰档不够用时靠线宽补，所以 (灰, 线宽) 的组合必须两两不同。
    # 把线宽表改平会让两条线彻底同貌，这里当场拦下。
    combos = list(zip(inks, widths))[:len(series)]
    if len(set(combos)) != len(combos):
        raise ValueError(f"S2 有两条线的（灰阶, 线宽）完全相同：{combos}")

    for si, (name, vs) in enumerate(series):
        d = "M" + " L".join(f"{S.T.px(sx(i))} {S.T.px(sy(v))}" for i, v in enumerate(vs))
        parts.append(S.path(d, inks[si], widths[si], cap="round"))

    # 线端标签
    want = [sy(vs[-1]) + T.SIZE["label"] * 0.35 for _, vs in series]
    ys = _place_labels(want, T.SIZE["label"] + 2.5, top + T.SIZE["label"], base)
    for si, (name, vs) in enumerate(series):
        parts.append(S.line(px1 + 1.5, sy(vs[-1]), px1 + 4.5,
                            ys[si] - T.SIZE["label"] * 0.35,
                            inks[si], T.STROKE["hairline"]))
        parts.append(S.text(px1 + 6, ys[si], name, T.SIZE["label"], inks[si]))

    # x 轴：标签太密就隔点抽稀，绝不缩字号
    parts.append(S.line(px0, base, px1, base, T.GRAY[3], T.STROKE["rule"]))
    step = 1
    while n / step > 1 and (px1 - px0) / (n / step) < S.text_width(
            max(x_labels, key=len), T.SIZE["label"]) + 6:
        step += 1
    for i, xl in enumerate(x_labels):
        if i % step:
            continue
        parts.append(S.text(sx(i), base + 3 + T.SIZE["label"], xl,
                            T.SIZE["label"], T.GRAY[3], anchor="middle"))

    H = base + axis_h + T.GAP["plot_source"] + T.SIZE["source"]
    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
