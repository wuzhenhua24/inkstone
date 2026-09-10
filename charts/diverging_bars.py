# -*- coding: utf-8 -*-
"""R2 分岔条 · 带正负的分类数值（≤10 项）"""
import tokens as T
from charts import _svg as S
from charts._data import require, num
from charts._data import decimals_for, fmt


MAX_CATS = 10


# ════ R2 分岔条 ════
# 数据形状：类目 → 可正可负的数值（增减、盈亏、净流入）
# 版心：single / a4body
# 失效：全为正 → R1 定序条；要看构成 → C1 百格方阵
def diverging_bars(data, title=None, subtitle=None, source=None,
                   column="single", unit="", sort=True):
    """data: [(类目, 数值), ...]，数值可正可负。"""
    if sort:
        data = sorted(data, key=lambda kv: -kv[1])
    require(data, "R2 分岔条")
    if len(data) > MAX_CATS:
        raise ValueError(
            f"R2 分岔条最多 {MAX_CATS} 项，收到 {len(data)} 项。"
            f"零点两侧都要留出条长和数值，再多每项只剩几毫米——改用 R1 或拆图。")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]

    dec = decimals_for([v for _, v in data])
    vmax = max((abs(v) for _, v in data), default=1) or 1
    val_w = max(S.text_width(num(v, unit, dec), T.SIZE["value"]) for _, v in data)

    # 两侧必须同一标度，否则「跌得比涨得多」这种判断会被画反。
    # 零点按正负极值的实际比例落位，两边共用同一个 pt/单位。
    pos = max((v for _, v in data if v > 0), default=0)
    neg = -min((v for _, v in data if v < 0), default=0)
    span = (x1 - x0) - 2 * (val_w + 4)
    unit_px = span / (pos + neg or 1)
    zx = x0 + val_w + 4 + neg * unit_px

    lab_h = T.SIZE["label"]
    bar_h = 4.5
    row_gap = 9.0
    row_h = lab_h + 3.0 + bar_h + row_gap

    top = S.head_height(title, subtitle, W)
    plot_h = row_h * len(data) - row_gap
    H = top + plot_h + T.GAP["plot_source"] + T.SIZE["source"] + 6

    parts = []
    for i, (name, v) in enumerate(data):
        y = top + i * row_h
        # 正负用明度分：正为主色，负退一档。不靠左右位置单独承担正负，
        # 缩印或裁切后位置线索会丢，明度不会。
        ink = T.GRAY[0] if v >= 0 else T.GRAY[2]
        parts.append(S.text(x0, y + lab_h,
                            S.ellipsize(name, x1 - x0 - 4, T.SIZE["label"]),
                            T.SIZE["label"], T.GRAY[2]))
        by = y + lab_h + 3.0
        bw = abs(v) * unit_px
        bx = zx if v >= 0 else zx - bw
        parts.append(S.rect(bx, by, bw, bar_h, ink))
        txt = num(v, unit, dec)
        if v >= 0:
            parts.append(S.text(zx + bw + 4, by + bar_h - 0.3, txt,
                                T.SIZE["value"], ink, T.WEIGHT["value"]))
        else:
            parts.append(S.text(zx - bw - 4, by + bar_h - 0.3, txt,
                                T.SIZE["value"], ink, T.WEIGHT["value"],
                                anchor="end"))

    parts.append(S.line(zx, top - 2, zx, top + plot_h, T.GRAY[3], T.STROKE["rule"]))
    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
