# -*- coding: utf-8 -*-
"""R3 点阵瀑布 · 可数单位的排名比较（项数多）"""
import tokens as T
from charts import _svg as S
from charts._data import fmt, require, require_nonneg


# ════ R3 点阵瀑布 ════
# 数据形状：类目 → 可数的整数量（次数、件数、人数），项数多于 R1 能容纳的
# 版心：single / a4body
# 失效：数值不可数（金额、比率）→ R1 定序条；只有几项 → R1
def dots_for(v, per_dot):
    """这一项要画几个点。和绘制循环用同一个式子，判定才和产物对得上。"""
    return max(1, int(round(v / per_dot)))


def per_dot_for(vmax, cap):
    """一个点代表几：最小的 1-2-5 阶梯值，使最大的一项摆得下 cap 个点。

    **用解的，不用查表。** 上一版是 (1,2,5,…,10000) 一张写死的表，
    需求一旦超过最大档，循环一次都不 break，per_dot 就停在初值 1——
    160 万的输入于是被照单全收，画出 160 万个 <circle>，几十 MB、
    几十米高的一张 SVG。不抛异常、不崩溃，校验器也判不出来（它不看几何），
    只是没法用。1-2-5 阶梯本身没有上限，写死一张表才有。

    提到模块级是为了能被直接测：这条逻辑一旦回退，测试要在一次函数调用里
    当场变红，而不是真的去画那 160 万个点、把测试自己挂死。
    """
    m = 0
    while dots_for(vmax, (1, 2, 5)[m % 3] * 10 ** (m // 3)) > cap:
        m += 1
    return (1, 2, 5)[m % 3] * 10 ** (m // 3)


def dot_cascade(data, title=None, subtitle=None, source=None,
                column="single", per_dot=None, unit="", max_rows=3, group=10):
    """data: [(类目, 整数量), ...]。per_dot 不传则自动定「一个点 = 几」。"""
    require(data, "R3 点阵瀑布")
    require_nonneg(data, "R3 点阵瀑布")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]
    inner = x1 - x0

    vmax = max(v for _, v in data) or 1
    r = T.DOT["r"]
    pitch = 2 * r + T.DOT["gap"] + 0.6
    # 每 group 个点空一格。不分组的点阵挤成一条实心带，数不出来——
    # 单位图的全部意义就是可数，数不出来它就只是一根难看的柱子。
    gsep = pitch * 0.9

    def row_width(k):
        return k * pitch + max(0, (k - 1) // group) * gsep

    per_row = 1
    while row_width(per_row + 1) <= inner:
        per_row += 1

    def dot_x(col):
        return x0 + r + col * pitch + (col // group) * gsep

    cap = per_row * max_rows
    if per_dot is None:
        per_dot = per_dot_for(vmax, cap)
    elif dots_for(vmax, per_dot) > cap:
        # 显式传进来的 per_dot 装不下时也不能闷头画——同一条错，
        # 只是这次错在调用方，那就把该传的值算给他。
        raise ValueError(
            f"R3 点阵瀑布：per_dot={per_dot} 时最大的一项要画 "
            f"{dots_for(vmax, per_dot):,} 个点，{column} 栏一张图最多摆得下 "
            f"{cap} 个（每行 {per_row} × {max_rows} 行）。"
            f"传 per_dot={per_dot_for(vmax, cap):,}，或者不传让它自己定。")

    lab_h = T.SIZE["label"]
    row_gap = 8.0
    top = S.head_height(title, subtitle, W)

    parts = []
    y = top
    for name, v in data:
        n_dots = max(1, int(round(v / per_dot)))
        lines = -(-n_dots // per_row)
        parts.append(S.text(x0, y + lab_h,
                            S.ellipsize(name, inner - 60, T.SIZE["label"]),
                            T.SIZE["label"], T.GRAY[2]))
        parts.append(S.text(x1, y + lab_h, fmt(v, 0) + unit, T.SIZE["value"],
                            T.GRAY[0], T.WEIGHT["value"], anchor="end"))
        dy = y + lab_h + 4 + r
        for k in range(n_dots):
            row, col = divmod(k, per_row)
            parts.append(S.circle(dot_x(col), dy + row * pitch, r, T.GRAY[1]))
        y = dy + (lines - 1) * pitch + r + row_gap

    H = y + T.GAP["plot_source"] + T.SIZE["source"] - row_gap + 4
    note = f"一个点 = {fmt(per_dot, 0)}{unit} · 每 {group} 点一组"
    src = f"{source} · {note}" if source else note
    return S.canvas(W, H, "\n".join(parts), title, subtitle, src)
