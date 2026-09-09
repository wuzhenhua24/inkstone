# -*- coding: utf-8 -*-
"""C1 百格方阵 · 100% 构成（≤6 类）"""
import tokens as T
from charts import _svg as S
from charts._data import decimals_for, require, require_nonneg

MAX_CATS = 6


# ════ C1 百格方阵 ════
# 数据形状：一个整体拆成若干部分，关心占比
# 版心：single / a4body
# 失效：>6 类 → 灰阶分不开，改用 R1 定序条；构成随时间变化 → C2 堆叠带
def hundred_grid(data, title=None, subtitle=None, source=None,
                 column="single", cols=10, grid_frac=0.56):
    """data: [(类目, 数值), ...]。数值可以是绝对数或百分比，函数内部归一。"""
    if len(data) > MAX_CATS:
        raise ValueError(
            f"C1 百格方阵最多 {MAX_CATS} 类，收到 {len(data)} 类。"
            f"灰阶只能可靠区分 6 档，再多印出来分不开——改用 R1 定序条。")

    require(data, "C1 百格方阵")
    # 负值会让「最大余额法」分出 165 格——一张号称百格的图画出 165 格，
    # 是这张图最容易被读者当场抓到的硬伤。
    require_nonneg(data, "C1 百格方阵")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]
    inner = x1 - x0

    total = sum(v for _, v in data) or 1
    pct = [v / total * 100 for _, v in data]

    # 最大余额法分配 100 格。逐类四舍五入会得到 99 或 101 格——
    # 一个号称"百格"的图画出 101 格，是最容易被读者抓到的硬伤。
    cells = [int(p) for p in pct]
    for i in sorted(range(len(data)), key=lambda i: -(pct[i] - int(pct[i])))[:100 - sum(cells)]:
        cells[i] += 1

    # 方阵只占版心的一部分，图例放右侧。
    # 满宽方阵会得到 6.6mm 的大格子——印出来是一堵墨墙，费墨且粗糙。
    rows = -(-100 // cols)
    slot = inner * grid_frac / cols
    cell = slot * 0.80
    grid_w = cols * slot - (slot - cell)
    grid_h = rows * slot - (slot - cell)

    lg_x = x0 + grid_w + 14
    lg_line = T.SIZE["label"] + 5.0
    top = S.head_height(title, subtitle, W)
    H = top + max(grid_h, lg_line * len(data)) + T.GAP["plot_source"] + T.SIZE["source"]

    # 按占比降序上墨：最大的一块最黑
    order = sorted(range(len(data)), key=lambda i: -cells[i])
    ink_of = {idx: T.GRAY[rank] for rank, idx in enumerate(order)}

    seq = []
    for idx in order:
        seq += [idx] * cells[idx]

    parts = []
    for k, idx in enumerate(seq):            # 按中文阅读顺序填：从左到右、自上而下
        r, c = divmod(k, cols)
        parts.append(S.rect(x0 + c * slot, top + r * slot, cell, cell, ink_of[idx]))

    # 接缝：六档灰里中间几档相邻时边界会糊，在每个类目的起始格左侧
    # 打一道竖线，明确"新类目从这里开始"。灰阶不够用时靠形状补，
    # 这是印刷的老办法——比再挤一档灰可靠。
    for k in range(1, len(seq)):
        if seq[k] == seq[k - 1]:
            continue
        r, c = divmod(k, cols)
        sx = x0 + c * slot - (slot - cell) / 2
        parts.append(S.line(sx, top + r * slot - 0.6,
                            sx, top + r * slot + cell + 0.6,
                            T.GRAY[0], 0.7))

    # 图例：一类一行，竖排。中文类目名不能缩写，横排图例在 85mm 里必然折行。
    decimals = decimals_for(pct)
    lg_avail = x1 - lg_x
    for row, idx in enumerate(order):
        y = top + T.SIZE["label"] + row * lg_line
        sw = T.SIZE["label"] * 0.8
        parts.append(S.rect(lg_x, y - sw + 0.5, sw, sw, ink_of[idx]))
        val = f"{pct[idx]:.{decimals}f}%"
        vw = S.text_width(val, T.SIZE["value"])
        parts.append(S.text(lg_x + sw + 3.5, y,
                            S.ellipsize(data[idx][0], lg_avail - sw - vw - 8, T.SIZE["label"]),
                            T.SIZE["label"], T.GRAY[1]))
        parts.append(S.text(x1, y, val, T.SIZE["value"], T.GRAY[0],
                            T.WEIGHT["value"], anchor="end"))

    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
