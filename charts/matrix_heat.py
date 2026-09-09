# -*- coding: utf-8 -*-
"""M1 矩阵热力 · 两个离散维度 × 数值（≤100 格）"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import require

MAX_CELLS = 100


# ════ M1 矩阵热力 ════
# 数据形状：行维度 × 列维度 → 数值。关心哪几格突出，也要能查具体数。
# 版心：double（170mm）
# 失效：>100 格 → 格内放不下数字，只剩色块，改用 R1 或拆表
def matrix_heat(rows, cols, values, title=None, subtitle=None, source=None,
                column="double", unit="", show_values=True):
    """rows / cols: 中文维度名列表；values: values[行][列] 的二维数值。"""
    require(rows, "M1 矩阵热力", "行维度")
    require(cols, "M1 矩阵热力", "列维度")
    bad = [i for i, row in enumerate(values) if len(row) != len(cols)]
    if len(values) != len(rows) or bad:
        raise ValueError(
            f"M1 矩阵热力的 values 必须是 {len(rows)}×{len(cols)} 的二维表，"
            f"收到 {len(values)} 行"
            + (f"，其中第 {bad[0]} 行有 {len(values[bad[0]])} 列" if bad else "") + "。")

    n = len(rows) * len(cols)
    if n > MAX_CELLS:
        raise ValueError(
            f"M1 矩阵热力最多 {MAX_CELLS} 格，收到 {n} 格。"
            f"再多格内放不下数字，灰阶单独承担不了查数——拆图或改用定序条。")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]

    # 行标签的装订线按实测宽度定。中文行名不能缩写，估宽会压到格子上。
    gut = max(S.text_width(r, T.SIZE["label"]) for r in rows) + 7
    gx = x0 + gut
    cw = (x1 - gx) / len(cols)
    ch = 21.0

    flat = [v for row in values for v in row]
    lo, hi = min(flat), max(flat)

    def level(v):
        """量化成 5 档。灰阶做连续标度不可靠——人眼在无参照时分不出
        60% 灰和 68% 灰，所以宁可离散化，再靠格内数字承担精确查询。"""
        if hi == lo:
            return len(T.HEAT) - 1
        return min(len(T.HEAT) - 1, int((v - lo) / (hi - lo) * len(T.HEAT)))

    col_lab_h = T.SIZE["label"] + 5
    top = S.head_height(title, subtitle, W)
    grid_top = top + col_lab_h
    grid_h = ch * len(rows)

    parts = []

    # 列标签：放不下就按实测宽度截断，不缩字号
    for j, c in enumerate(cols):
        parts.append(S.text(gx + cw * (j + 0.5), top + T.SIZE["label"],
                            S.ellipsize(c, cw - 3, T.SIZE["label"]),
                            T.SIZE["label"], T.GRAY[2], anchor="middle"))

    for i, r in enumerate(rows):
        y = grid_top + i * ch
        parts.append(S.text(gx - 5, y + ch / 2 + T.SIZE["label"] * 0.35,
                            r, T.SIZE["label"], T.GRAY[2], anchor="end"))
        for j in range(len(cols)):
            v = values[i][j]
            lv = level(v)
            bg = T.HEAT[lv]
            # 格间留 0.8pt 纸缝，胶印套不准时格子也不会连成一片
            parts.append(S.rect(gx + cw * j + 0.4, y + 0.4, cw - 0.8, ch - 0.8, bg))
            if show_values:
                dark = lv >= T.HEAT_FLIP
                parts.append(S.text(
                    gx + cw * (j + 0.5), y + ch / 2 + T.SIZE["value"] * 0.35,
                    f"{v:,g}{unit}", T.SIZE["value"],
                    T.PAPER if dark else T.GRAY[0], T.WEIGHT["value"],
                    anchor="middle", on=bg,
                    on_box=(gx + cw * j + 0.4, y + 0.4, cw - 0.8, ch - 0.8)))

    # 标度图例：五档色阶 + 两端数值
    ly = grid_top + grid_h + 12
    sw, sh = 16.0, 6.0
    parts.append(S.text(x0, ly + sh - 1, "低", T.SIZE["label"], T.GRAY[3]))
    lx = x0 + S.text_width("低", T.SIZE["label"]) + 4
    for k, c in enumerate(T.HEAT):
        parts.append(S.rect(lx + k * (sw + 1.2), ly, sw, sh, c))
    lx2 = lx + len(T.HEAT) * (sw + 1.2) + 2
    parts.append(S.text(lx2, ly + sh - 1, f"高 · {lo:,g}–{hi:,g}{unit}",
                        T.SIZE["label"], T.GRAY[3]))

    H = ly + sh + T.GAP["plot_source"] + T.SIZE["source"] + 2
    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
