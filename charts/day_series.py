# -*- coding: utf-8 -*-
"""S1 日序条码 · 每天一个读数的长序列（60–120 天）"""
import sys, os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import median, require, require_nonneg


MAX_DAYS = 150


# ════ S1 日序条码 ════
# 数据形状：每天一个读数，60–120 天。保留每一天，不做周聚合。
# 版心：double（170mm）——90 天在单栏里每天只剩 2.5pt，条会糊成一片
# 失效：>150 天改用周聚合；多序列对比改用 S2 细线族
def day_series(data, title=None, subtitle=None, source=None,
               column="double", unit="", annotate_top=2, show_median=True,
               annotate_ratio=1.25):
    """data: [(datetime.date, 数值), ...] 按时间升序。"""
    require(data, "S1 日序条码", "序列")
    if len(data) > MAX_DAYS:
        raise ValueError(
            f"S1 日序条码最多 {MAX_DAYS} 天，收到 {len(data)} 天。"
            f"再多每天不足 0.35pt 的印刷地板，条会糊成一片实心带——"
            f"先做周聚合再画。")
    require_nonneg([(str(d), v) for d, v in data], "S1 日序条码")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]
    inner = x1 - x0
    n = len(data)

    vmax = max(v for _, v in data) or 1

    # 中位数标签要占掉右侧一条装订线，条必须止步于此——
    # 否则标签压在数据上。屏幕图可以靠 tooltip 躲，印刷没有这条退路。
    # 这一段必须排在算高度之前：图形区高度由图形区宽度定，而图形区
    # 右界正是被这条装订线切出来的。
    med = median([v for _, v in data]) if show_median else None
    med_lab = f"中位数 {med:,g}{unit}" if show_median else ""
    gutter = (S.text_width(med_lab, T.SIZE["label"]) + 6) if show_median else 0
    px1 = x1 - gutter                       # 图形区右界

    annot_h = T.SIZE["value"] + 5      # 峰值标注带
    plot_h = T.plot_height(px1 - x0, "barcode")
    axis_h = T.SIZE["label"] + 6

    top = S.head_height(title, subtitle, W)
    base_y = top + annot_h + plot_h    # 基线
    H = base_y + axis_h + T.GAP["plot_source"] + T.SIZE["source"] + 4

    slot = (px1 - x0) / n
    bar_w = max(T.STROKE["hairline"], min(3.2, slot * 0.68))

    parts = []
    med_box = None

    # ── 中位线：长序列里"这一天算高还是低"需要一条参照，否则只能看形状
    if show_median:
        my = base_y - plot_h * med / vmax
        parts.append(S.line(x0, my, px1 + 3, my, T.GRAY[4], T.STROKE["rule"], dash="2 2"))
        parts.append(S.text(x1, my + T.SIZE["label"] * 0.35, med_lab,
                            T.SIZE["label"], T.GRAY[3], anchor="end"))
        med_box = (px1 + 3, my - T.SIZE["label"], x1, my + T.SIZE["label"])

    # ── 逐日条
    for i, (d, v) in enumerate(data):
        cx = x0 + slot * (i + 0.5)
        h = plot_h * v / vmax
        parts.append(S.rect(cx - bar_w / 2, base_y - h, bar_w, h, T.GRAY[1]))

    parts.append(S.line(x0, base_y, px1, base_y, T.GRAY[3], T.STROKE["rule"]))

    # ── 月份刻度：中文月份标签，只在每月第一天出现
    seen = set()
    for i, (d, _) in enumerate(data):
        if d.month in seen:
            continue
        seen.add(d.month)
        cx = x0 + slot * (i + 0.5)
        if cx > px1 - 12:
            continue
        parts.append(S.line(cx, base_y, cx, base_y + 3, T.GRAY[3], T.STROKE["rule"]))
        parts.append(S.text(cx, base_y + 3 + T.SIZE["label"], f"{d.month}月",
                            T.SIZE["label"], T.GRAY[3]))

    # ── 峰值标注 + 防重叠
    # barcode 的老教训：相邻高点的标注会叠在一起。这里按 x 排序后强制最小
    # 间距，挤不下就丢掉数值较小的那个——宁可少标，不许压字。
    # annotate_top 是上限不是配额：只标显著高于中位数的点（默认 1.25×）。
    # 把第 2、3 名硬标出来，读者会以为那也是异常——那是噪音不是信息。
    ref = median([v for _, v in data])
    ranked = [i for i in sorted(range(n), key=lambda i: -data[i][1])[:annotate_top]
              if data[i][1] >= ref * annotate_ratio]
    cands = []
    for i in sorted(ranked):
        d, v = data[i]
        txt = f"{d.month}月{d.day}日 {v:,g}{unit}"
        cands.append({"i": i, "v": v, "txt": txt,
                      "cx": x0 + slot * (i + 0.5),
                      "w": S.text_width(txt, T.SIZE["value"])})

    placed = []
    for c in cands:
        lo = max(x0, min(px1 - c["w"], c["cx"] - c["w"] / 2))   # 夹进图形区
        hi = lo + c["w"]
        d, v = data[c["i"]]
        ty = base_y - plot_h * v / vmax - 4
        clash = any(not (hi + 6 < p["lo"] or lo - 6 > p["hi"]) for p in placed)
        # 也要避开中位数标签盒：低矮的"峰"标注恰好落在中位线高度时会撞上
        if med_box and not clash:
            mx0, my0, mx1, my1 = med_box
            clash = (hi + 4 > mx0 and lo - 4 < mx1
                     and ty > my0 - T.SIZE["value"] and ty - T.SIZE["value"] < my1)
        if clash:
            continue                                # 挤不下就不标
        placed.append({"lo": lo, "hi": hi, **c})

    for p in placed:
        h = plot_h * data[p["i"]][1] / vmax
        parts.append(S.rect(p["cx"] - bar_w / 2, base_y - h, bar_w, h, T.GRAY[0]))
        parts.append(S.text(p["lo"], base_y - h - 4, p["txt"], T.SIZE["value"],
                            T.GRAY[0], T.WEIGHT["value"]))

    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
