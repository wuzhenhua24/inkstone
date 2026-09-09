# -*- coding: utf-8 -*-
"""C2 堆叠带 · 构成随时间变化（≤5 层）"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import nice_ticks, decimals_for, fmt, require, require_nonneg
from charts.line_family import _place_labels

MAX_LAYERS = 5


# ════ C2 堆叠带 ════
# 数据形状：若干构成项随连续时间变化，既看总量也看构成
# 版心：double（170mm）
# 失效：只看某一期构成 → C1 百格方阵；只看总量 → S1；层间要读交叉 → S2
def stacked_bands(layers, x_labels, title=None, subtitle=None, source=None,
                  column="double", unit=""):
    """layers: [(名称, [数值, ...]), ...]，自下而上堆叠。第一层在最下。"""
    if len(layers) > MAX_LAYERS:
        raise ValueError(
            f"C2 堆叠带最多 {MAX_LAYERS} 层，收到 {len(layers)} 层。"
            f"再多带会薄到放不下名字，且灰阶排不开——合并小项或改用 C1。")

    require(layers, "C2 堆叠带", "层")
    require(x_labels, "C2 堆叠带", "时间刻度")
    for nm, vs in layers:
        if len(vs) != len(x_labels):
            raise ValueError(
                f"C2 堆叠带的「{nm}」层有 {len(vs)} 个读数，"
                f"时间刻度却有 {len(x_labels)} 个——两者必须等长。")
    # 堆叠的前提是各层同号：混入负层，带的上沿会低于下沿，多边形自交，
    # 印出来是一团看不出构成的墨。
    require_nonneg([(nm, v) for nm, vs in layers for v in vs],
                   "C2 堆叠带", "R2 分岔条或 S2 细线族")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]
    n = len(x_labels)

    totals = [sum(vs[i] for _, vs in layers) for i in range(n)]
    ticks = nice_ticks(0, max(totals))
    ymax = ticks[-1]

    lab_w = max(S.text_width(nm, T.SIZE["label"]) for nm, _ in layers)
    px0 = x0 + max(S.text_width(f"{t:,g}", T.SIZE["label"]) for t in ticks) + 4
    px1 = x1 - lab_w - 7        # 薄带的名字要退到右侧，先把位置留出来

    plot_h = T.plot_height(px1 - px0, "band")
    top = S.head_height(title, subtitle, W)
    base = top + plot_h

    def sx(i):
        return px0 + (px1 - px0) * i / max(1, n - 1)

    def sy(v):
        return base - plot_h * v / (ymax or 1)

    parts = []
    for t in ticks:
        parts.append(S.line(px0, sy(t), px1, sy(t), T.GRAY[6], T.STROKE["hairline"]))
        parts.append(S.text(px0 - 4, sy(t) + T.SIZE["label"] * 0.35, f"{t:,g}",
                            T.SIZE["label"], T.GRAY[3], anchor="end"))

    # 逐层累加，画成闭合多边形
    lower = [0.0] * n
    bands = []
    for li, (name, vs) in enumerate(layers):
        upper = [lower[i] + vs[i] for i in range(n)]
        top_pts = [f"{T.px(sx(i))} {T.px(sy(upper[i]))}" for i in range(n)]
        bot_pts = [f"{T.px(sx(i))} {T.px(sy(lower[i]))}" for i in range(n - 1, -1, -1)]
        d = "M" + " L".join(top_pts + bot_pts) + " Z"
        parts.append(f'<path d="{d}" fill="{T.BAND[li]}"/>')
        bands.append((name, list(lower), upper))
        lower = upper

    # 带内标签不能只看「最厚的那一列」。带是随时间变化的多边形，
    # 最厚处往往在末列，标签居中一放就有半个字飘到带外——深带上的
    # 白字飘到白纸上，灰度审阅时根本看不出来。
    # 正确做法是搜一个「整块标签矩形都在带内」的位置。
    need = T.SIZE["label"] + 4

    def fit_box(lo, up, w):
        """找一个宽 w、高 need 的矩形能整块放进带内的位置，返回 (cx, cy)。"""
        best = None
        for i in range(n):
            cx = min(max(sx(i), px0 + w / 2), px1 - w / 2)
            if cx - w / 2 < px0 - .01 or cx + w / 2 > px1 + .01:
                continue
            # 矩形横跨的所有列（含两端插值）都要够厚
            cov = [j for j in range(n) if cx - w / 2 - 1e-9 <= sx(j) <= cx + w / 2 + 1e-9]
            edges = []
            for ex in (cx - w / 2, cx + w / 2):
                t = (ex - px0) / ((px1 - px0) / max(1, n - 1))
                j0 = max(0, min(n - 2, int(t)))
                f = t - j0
                edges.append((lo[j0] + (lo[j0 + 1] - lo[j0]) * f,
                              up[j0] + (up[j0 + 1] - up[j0]) * f))
            tops = [up[j] for j in cov] + [e[1] for e in edges]
            bots = [lo[j] for j in cov] + [e[0] for e in edges]
            clear = sy(max(bots)) - sy(min(tops))
            if clear >= need and (best is None or clear > best[0]):
                best = (clear, cx, (sy(max(bots)) + sy(min(tops))) / 2)
        return (best[1], best[2]) if best else None

    inside, outside = [], []
    for li, (name, lo, up) in enumerate(bands):
        w = S.text_width(name, T.SIZE["label"])
        spot = fit_box(lo, up, w)
        if spot:
            inside.append((li, name, w, spot[0], spot[1]))
        else:
            outside.append((li, name, (sy(lo[n - 1]) + sy(up[n - 1])) / 2))

    for li, name, w, cx, cy in inside:
        # 声明底色矩形，让校验器确认底色真的盖住了整段文字
        parts.append(S.text(cx, cy + T.SIZE["label"] * 0.35, name, T.SIZE["label"],
                            T.PAPER if li < T.BAND_FLIP else T.GRAY[0],
                            T.WEIGHT["value"], anchor="middle", on=T.BAND[li],
                            on_box=(cx - w / 2, cy - need / 2, w, need)))

    if outside:
        ys = _place_labels([c for _, _, c in outside],
                           T.SIZE["label"] + 2.5, top + T.SIZE["label"], base)
        for (li, name, cy), y in zip(outside, ys):
            parts.append(S.line(px1 + 1.5, cy, px1 + 4.5, y - T.SIZE["label"] * 0.35,
                                T.GRAY[3], T.STROKE["hairline"]))
            parts.append(S.text(px1 + 6, y, name, T.SIZE["label"], T.GRAY[1]))

    parts.append(S.line(px0, base, px1, base, T.GRAY[3], T.STROKE["rule"]))
    step = 1
    xl_w = S.widest(x_labels, T.SIZE["label"])   # 实测最宽，不是字符最多
    while n / step > 1 and (px1 - px0) / (n / step) < xl_w + 6:
        step += 1
    for i, xl in enumerate(x_labels):
        if i % step == 0:
            parts.append(S.text(sx(i), base + 3 + T.SIZE["label"], xl,
                                T.SIZE["label"], T.GRAY[3], anchor="middle"))

    H = base + T.SIZE["label"] + 8 + T.GAP["plot_source"] + T.SIZE["source"]
    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
