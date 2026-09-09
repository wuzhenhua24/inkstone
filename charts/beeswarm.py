# -*- coding: utf-8 -*-
"""D2 蜂群 · 逐条记录的堆积分布（40–180 点，≤6 组）"""
import tokens as T
from charts import _svg as S
from charts._data import median, nice_ticks, require, num

MAX_GROUPS = 6
MAX_POINTS = 180


def _pack(xs, r, gap):
    """蜂群装箱：每个点放在离中轴最近、且不与已放置点相撞的位置。

    按 x 升序处理，碰撞只需回看 x 距离在 2r+gap 以内的点——
    这让复杂度从 O(n²) 降到接近 O(n·k)，180 点以内瞬时完成。

    窗口用一个左指针推进，不是每个点都把 placed 全扫一遍：placed 是按
    x 升序追加的，所以「x 距离在 d 以内」的那些点必然是尾部一段连续切片。
    全扫一遍写起来更短，但那样复杂度还是 O(n²)，上面这句话就成了空话。
    """
    d = 2 * r + gap
    placed = []
    out = []
    lo = 0
    for x in sorted(xs):
        while lo < len(placed) and x - placed[lo][0] >= d:
            lo += 1
        near = placed[lo:]
        y, k = 0.0, 0
        while True:
            for cand in ((0.0,) if k == 0 else (k * r, -k * r)):
                if all((x - px) ** 2 + (cand - py) ** 2 >= d * d - 1e-9
                       for px, py in near):
                    y = cand
                    break
            else:
                k += 1
                continue
            break
        placed.append((x, y))
        out.append((x, y))
    return out


# ════ D2 蜂群 ════
# 数据形状：逐条记录的单变量分布，按组比较。拒绝聚合，摊开原材料。
# 版心：double（170mm）——单栏里点会挤成一条线
# 失效：>180 点 → D1 阶梯直方；>6 组 → 拆图；只关心分位数 → D3 五数摘要
def beeswarm(groups, title=None, subtitle=None, source=None,
             column="double", unit="", r=None, show_median=True):
    """groups: [(组名, [数值, ...]), ...]"""
    if len(groups) > MAX_GROUPS:
        raise ValueError(
            f"D2 蜂群最多 {MAX_GROUPS} 组，收到 {len(groups)} 组。"
            f"再多每组只剩几毫米高，点会糊成一条线——拆成多张图。")

    require(groups, "D2 蜂群", "组")
    n_pts = sum(len(vs) for _, vs in groups)
    if n_pts > MAX_POINTS:
        raise ValueError(
            f"D2 蜂群最多 {MAX_POINTS} 点，收到 {n_pts} 点。"
            f"再多点会堆成密不透风的块，逐条记录这件事本身就没了意义——"
            f"改用 D1 阶梯直方。")
    for nm, vs in groups:
        require(vs, "D2 蜂群", f"「{nm}」组的读数")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]
    r = max(T.DOT["min_r"], r or T.DOT["r"])
    gap = T.DOT["gap"]

    allv = [v for _, vs in groups for v in vs]
    lo, hi = min(allv), max(allv)
    ticks = nice_ticks(lo, hi)
    dlo, dhi = min(lo, ticks[0]), max(hi, ticks[-1])

    # 中位数标注要占右侧装订线，点必须止步于此
    med_w = max(S.text_width(f"中位数 {num(median(vs), unit)}", T.SIZE["label"])
                for _, vs in groups) if show_median else 0
    px1 = x1 - (med_w + 8 if show_median else 0)

    def sx(v):
        return x0 + (px1 - x0) * (v - dlo) / (dhi - dlo or 1)

    lab_h = T.SIZE["label"]
    axis_h = T.SIZE["label"] + 8
    top = S.head_height(title, subtitle, W)

    # 先装箱，再按实际堆叠高度定每组的行高——留固定高度要么浪费要么截断
    packed, halves = [], []
    for _, vs in groups:
        pts = _pack([sx(v) for v in vs], r, gap)
        packed.append(pts)
        halves.append(max((abs(y) for _, y in pts), default=0) + r)

    parts = []
    y_cursor = top
    for gi, (name, vs) in enumerate(groups):
        half = halves[gi]
        parts.append(S.text(x0, y_cursor + lab_h, name, T.SIZE["label"], T.GRAY[2]))
        cy = y_cursor + lab_h + 3 + half

        for px, py in packed[gi]:
            parts.append(S.circle(px, cy + py, r, T.GRAY[1]))

        if show_median:
            m = median(vs)
            mx = sx(m)
            parts.append(S.line(mx, cy - half - 1.5, mx, cy + half + 1.5,
                                T.GRAY[0], T.STROKE["data"]))
            parts.append(S.text(x1, cy + T.SIZE["label"] * 0.35,
                                f"中位数 {num(m, unit)}", T.SIZE["label"],
                                T.GRAY[3], anchor="end"))
        y_cursor = cy + half + 11

    # 共享 x 轴
    ay = y_cursor - 3
    parts.append(S.line(x0, ay, px1, ay, T.GRAY[3], T.STROKE["rule"]))
    for t in ticks:
        tx = sx(t)
        parts.append(S.line(tx, ay, tx, ay + 3, T.GRAY[3], T.STROKE["rule"]))
        parts.append(S.text(tx, ay + 3 + T.SIZE["label"], num(t),
                            T.SIZE["label"], T.GRAY[3], anchor="middle"))

    H = ay + axis_h + T.GAP["plot_source"] + T.SIZE["source"]
    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
