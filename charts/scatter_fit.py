# -*- coding: utf-8 -*-
"""M2 散点带回归 · 两个连续变量"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import linreg, nice_ticks, fmt, decimals_for, require


# ════ M2 散点带回归 ════
# 数据形状：同一批实体上的两个连续变量，看是否共变
# 版心：single / a4body
# 失效：n<20 拟合线没有意义，关掉 fit；分组比较 → 分面用 S3
def scatter_fit(points, title=None, subtitle=None, source=None,
                column="single", x_unit="", y_unit="", x_name="", y_name="",
                fit=True, min_n_for_fit=20):
    """points: [(x, y), ...]"""
    require(points, "M2 散点带回归", "点")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]

    xt = nice_ticks(min(xs), max(xs), 5)
    yt = nice_ticks(min(ys), max(ys), 4)
    px0 = x0 + max(S.text_width(f"{t:,g}", T.SIZE["label"]) for t in yt) + 4
    plot_h = 96.0
    top = S.head_height(title, subtitle, W)
    base = top + plot_h

    def sx(v):
        return px0 + (x1 - px0) * (v - xt[0]) / (xt[-1] - xt[0] or 1)

    def sy(v):
        return base - plot_h * (v - yt[0]) / (yt[-1] - yt[0] or 1)

    parts = []
    for t in yt:
        parts.append(S.line(px0, sy(t), x1, sy(t), T.GRAY[6], T.STROKE["hairline"]))
        parts.append(S.text(px0 - 4, sy(t) + T.SIZE["label"] * 0.35, f"{t:,g}",
                            T.SIZE["label"], T.GRAY[3], anchor="end"))

    do_fit = fit and len(points) >= min_n_for_fit
    if do_fit:
        slope, inter, r = linreg(xs, ys)
        # 拟合线只画在数据实际覆盖的 x 区间内，不外推到坐标轴两端——
        # 延伸出去的那一段是没有数据支撑的猜测。
        a, b = min(xs), max(xs)
        parts.append(S.path(
            f"M{T.px(sx(a))} {T.px(sy(slope * a + inter))} "
            f"L{T.px(sx(b))} {T.px(sy(slope * b + inter))}",
            T.GRAY[3], T.STROKE["data"], cap="round"))

    for x, y in points:
        parts.append(S.circle(sx(x), sy(y), T.DOT["r"] * 0.85, T.GRAY[1], opacity=0.8))

    parts.append(S.line(px0, base, x1, base, T.GRAY[3], T.STROKE["rule"]))
    dec = decimals_for(xt)
    for t in xt:
        parts.append(S.text(sx(t), base + 3 + T.SIZE["label"], fmt(t, dec),
                            T.SIZE["label"], T.GRAY[3], anchor="middle"))

    axis_note = " · ".join(p for p in (
        f"横轴 {x_name}{x_unit}" if x_name else "",
        f"纵轴 {y_name}{y_unit}" if y_name else "") if p)
    # r 和 n 必须写出来。一条拟合线不带这两个数，读者无从判断它算不算数。
    stat = (f"n={len(points)} · r={r:+.2f}" if do_fit
            else f"n={len(points)} · 样本不足 {min_n_for_fit}，未拟合")
    src = " · ".join(p for p in (source, axis_note, stat) if p)
    H = base + T.SIZE["label"] + 8 + T.GAP["plot_source"] + T.SIZE["source"]
    return S.canvas(W, H, "\n".join(parts), title, subtitle, src)
