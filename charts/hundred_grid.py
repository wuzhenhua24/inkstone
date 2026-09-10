# -*- coding: utf-8 -*-
"""C1 百格方阵 · 100% 构成（≤6 类）"""
import tokens as T
from charts import _svg as S
from charts._data import decimals_for, require, require_nonneg

MAX_CATS = 6
# 方阵与图例之间的最大空隙。超过这个数就不再把图例推到版心右边缘——
# 254mm 的幻灯片档上右对齐会让「类目3」和「15.2%」之间裂开 130mm。
LEGEND_GAP_MAX = 48.0


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
    # 格子随栏宽线性长，所以 grid_frac 这个系数在窄栏够用、在宽栏不够：
    # 254mm 的幻灯片档上格子会长到 11mm 见方，正是上面那句「墨墙」说的东西，
    # 整图也因此高到 157mm，塞不进一张 16:9 的幻灯片。
    # 格子尺寸是印刷手感，不是版心的函数——同一张百格方阵在期刊上和在
    # 幻灯片上应该长得一样大，宽栏多出来的地方留白，不用来把格子吹大。
    slot = min(inner * grid_frac / cols, T.GRID_CELL_MAX / 0.80)
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
    sw = T.SIZE["label"] * 0.8
    vals = [f"{p:.{decimals}f}%" for p in pct]
    # 图例块的宽度由内容决定，不由版心决定。把百分比右对齐到版心右缘，
    # 窄栏上正好，宽栏上就会在类目名和数字之间裂开一大片空白——格子封顶
    # 之后 slide 档实测裂了 130mm，读者的视线要横跨半张幻灯片才能把
    # 「类目3」和「15.2%」对上。校验器判不出这个：没越界、没压字。
    #
    # 但也不能就近贴着方阵排完了事：那样窄栏上整块内容会缩在左边，
    # 右侧留出一个 9mm 的洞（实测 c1 左边距 1.5mm、右边距 8.9mm，
    # 而别的图两边都是 2mm）——1:1 落纸齐左置入，右边就空一块。
    # 规则是**让空隙吸收余量，但给空隙封顶**：窄栏顶满右边缘，
    # 宽栏不把类目名和百分比拉开半张幻灯片。
    lg_w = (sw + 3.5 + S.widest([n for n, _ in data], T.SIZE["label"])
            + 8 + S.widest(vals, T.SIZE["value"]))
    # 写成连续的：空隙取「右对齐所需」和「上限」里的小者，再兜一个下限。
    # 写成阈值判断会有阶跃——刚过阈值那一档会从「顶满」突然掉成一个大洞。
    lg_x = max(x0 + grid_w + 14.0,
               min(x1 - lg_w, x0 + grid_w + LEGEND_GAP_MAX))
    lg_right = lg_x + lg_w
    lg_avail = lg_w
    for row, idx in enumerate(order):
        y = top + T.SIZE["label"] + row * lg_line
        parts.append(S.rect(lg_x, y - sw + 0.5, sw, sw, ink_of[idx]))
        val = vals[idx]
        vw = S.text_width(val, T.SIZE["value"])
        parts.append(S.text(lg_x + sw + 3.5, y,
                            S.ellipsize(data[idx][0], lg_avail - sw - vw - 8, T.SIZE["label"]),
                            T.SIZE["label"], T.GRAY[1]))
        parts.append(S.text(lg_right, y, val, T.SIZE["value"], T.GRAY[0],
                            T.WEIGHT["value"], anchor="end"))

    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
