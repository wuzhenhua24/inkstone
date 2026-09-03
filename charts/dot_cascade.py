# -*- coding: utf-8 -*-
"""R3 点阵瀑布 · 可数单位的排名比较（项数多）"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import fmt


# ════ R3 点阵瀑布 ════
# 数据形状：类目 → 可数的整数量（次数、件数、人数），项数多于 R1 能容纳的
# 版心：single / a4body
# 失效：数值不可数（金额、比率）→ R1 定序条；只有几项 → R1
def dot_cascade(data, title=None, subtitle=None, source=None,
                column="single", per_dot=None, unit="", max_rows=3, group=10):
    """data: [(类目, 整数量), ...]。per_dot 不传则自动定「一个点 = 几」。"""
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

    # 一个点代表几，由「最大的一项要摆得下」倒推，并取整成人读得懂的数
    if per_dot is None:
        need = vmax / (per_row * max_rows)
        per_dot = 1
        for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000,
                     2000, 5000, 10000):
            if step >= need:
                per_dot = step
                break

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
