# -*- coding: utf-8 -*-
"""D3 五数摘要 · 分位数 + 异常值（≤8 组）"""
import tokens as T
from charts import _svg as S
from charts._data import five_number, nice_ticks, require, num

MAX_GROUPS = 8


# ════ D3 五数摘要 ════
# 数据形状：分组连续分布，只关心分位数和异常值，不需要看到每一条记录
# 版心：single / a4body
# 失效：要看每条记录 → D2 蜂群；单组无对比 → D1 阶梯直方
def tick_box(groups, title=None, subtitle=None, source=None,
             column="single", unit="", show_n=True):
    """groups: [(组名, [数值, ...]), ...]"""
    if len(groups) > MAX_GROUPS:
        raise ValueError(
            f"D3 五数摘要最多 {MAX_GROUPS} 组，收到 {len(groups)} 组。"
            f"再多每组只剩几毫米，箱体和须线分不开——拆图。")

    require(groups, "D3 五数摘要", "组")
    for nm, vs in groups:
        require(vs, "D3 五数摘要", f"「{nm}」组的读数")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]

    stats = [five_number(vs) for _, vs in groups]
    allv = [v for _, vs in groups for v in vs]
    ticks = nice_ticks(min(allv), max(allv))
    dlo, dhi = ticks[0], ticks[-1]

    def sx(v):
        return x0 + (x1 - x0) * (v - dlo) / (dhi - dlo or 1)

    lab_h = T.SIZE["label"]
    box_h = 7.0
    row_gap = 11.0
    row_h = lab_h + 3.5 + box_h + row_gap
    axis_h = T.SIZE["label"] + 8

    top = S.head_height(title, subtitle, W)
    plot_h = row_h * len(groups) - row_gap
    ay = top + plot_h + 4

    parts = []

    # 刻度网格先画，让所有记号压在它上面
    for t in ticks:
        parts.append(S.line(sx(t), top, sx(t), ay, T.GRAY[6], T.STROKE["hairline"]))

    for gi, ((name, _), st) in enumerate(zip(groups, stats)):
        y = top + gi * row_h
        head = f"{name}   n={st['n']}" if show_n else name
        parts.append(S.text(x0, y + lab_h, head, T.SIZE["label"], T.GRAY[2]))

        cy = y + lab_h + 3.5 + box_h / 2
        # 须线：止于最远的非异常值，不是止于 1.5IQR 的计算端点
        parts.append(S.line(sx(st["lo"]), cy, sx(st["hi"]), cy,
                            T.GRAY[3], T.STROKE["rule"]))
        for v in (st["lo"], st["hi"]):
            parts.append(S.line(sx(v), cy - 2.2, sx(v), cy + 2.2,
                                T.GRAY[3], T.STROKE["rule"]))

        # 箱体用浅填充而不是描边——印刷上细描边框在缩印后会糊成实线
        bx, bw = sx(st["q1"]), sx(st["q3"]) - sx(st["q1"])
        parts.append(S.rect(bx, cy - box_h / 2, bw, box_h, T.GRAY[5]))
        # 中位数是这张图唯一要一眼看到的量，给它全图最重的笔画
        parts.append(S.line(sx(st["med"]), cy - box_h / 2 - 1.5,
                            sx(st["med"]), cy + box_h / 2 + 1.5,
                            T.GRAY[0], T.STROKE["bold"]))
        for v in st["outliers"]:
            parts.append(S.circle(sx(v), cy, T.DOT["r"] * 0.8, T.GRAY[1]))

    # 共享 x 轴
    parts.append(S.line(x0, ay, x1, ay, T.GRAY[3], T.STROKE["rule"]))
    for t in ticks:
        parts.append(S.text(sx(t), ay + 3 + T.SIZE["label"], num(t),
                            T.SIZE["label"], T.GRAY[3], anchor="middle"))

    H = ay + axis_h + T.GAP["plot_source"] + T.SIZE["source"]
    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
