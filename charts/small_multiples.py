# -*- coding: utf-8 -*-
"""S3 小倍数网格 · 多实体各自一条序列（≤12 格）"""
import tokens as T
from charts import _svg as S
from charts._data import nice_ticks, decimals_for, fmt, require, require_nonneg, num

MAX_PANELS = 12


# ════ S3 小倍数网格 ════
# 数据形状：多个实体，每个各有一条同单位、同时间轴的序列
# 版心：double（170mm）
# 失效：≤6 条且要读交叉 → S2 细线族；单实体 → S1 日序条码
def small_multiples(panels, x_labels, title=None, subtitle=None, source=None,
                    column="double", cols=None, unit="", shared_scale=True):
    """panels: [(名称, [数值, ...]), ...]，按重要性或大小降序传入。"""
    if len(panels) > MAX_PANELS:
        raise ValueError(
            f"S3 小倍数网格最多 {MAX_PANELS} 格，收到 {len(panels)} 格。"
            f"再多每格放不下中文名——拆成多张图。")

    require(panels, "S3 小倍数网格", "格")
    for nm, vs in panels:
        require(vs, "S3 小倍数网格", f"「{nm}」格的读数")
    require_nonneg([(nm, v) for nm, vs in panels for v in vs],
                   "S3 小倍数网格", "S2 细线族并关掉零起点")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]
    inner = x1 - x0

    allv = [v for _, vs in panels for v in vs]
    gmax = max(allv)
    ticks = nice_ticks(0, gmax)
    ymax_shared = ticks[-1]

    # 每格至少要放得下「名字 + 末值」。放不下就减列——绝不缩字号，
    # 也不把中文名截断成认不出的样子。这是版面组装第一条硬约束。
    dec = decimals_for([vs[-1] for _, vs in panels])
    lab_w = max(S.text_width(n, T.SIZE["label"]) for n, _ in panels)
    val_w = max(S.text_width(fmt(vs[-1], dec) + unit, T.SIZE["value"])
                for _, vs in panels)
    min_pw = lab_w + val_w + 12

    gap = 9.0
    npanel = len(panels)

    def panel_w(c):
        return (inner - gap * (c - 1)) / c

    def panel_plot_h(w):
        # 格高由格宽定，目标宽高比 2.2:1。太扁看不出形状，太方浪费版面。
        return max(26.0, min(54.0, w / 2.2))

    # 选列不能只看「装得下」——那会选出最多的列数，格子又扁又宽，
    # 折线压成一条直线，小倍数就白做了。同时还要少留空格。
    if cols is None:
        best, cols = None, 1
        for c in range(1, min(6, npanel) + 1):
            w = panel_w(c)
            if w < min_pw:
                continue
            aspect = w / panel_plot_h(w)
            orphans = -(-npanel // c) * c - npanel
            score = abs(aspect - 2.2) + orphans * 0.35
            if best is None or score < best:
                best, cols = score, c

    pw = panel_w(cols)
    if pw < min_pw:
        raise ValueError(
            f"每格只有 {pw:.1f}pt，放不下「"
            f"{max(panels, key=lambda p: S.text_width(p[0], T.SIZE['label']))[0]}」"
            f"加末值（需 {min_pw:.1f}pt）。减少列数、换双栏，或缩短名称。")

    rows = -(-npanel // cols)
    lab_h = T.SIZE["label"]
    plot_h = panel_plot_h(pw)
    ph = lab_h + 5 + plot_h + 12

    top = S.head_height(title, subtitle, W)
    n = len(x_labels)
    parts = []

    for pi, (name, vs) in enumerate(panels):
        r, c = divmod(pi, cols)
        gx = x0 + c * (pw + gap)
        gy = top + r * ph
        ymax = ymax_shared if shared_scale else (max(vs) or 1)
        base = gy + lab_h + 5 + plot_h

        def sx(i, _gx=gx):
            return _gx + pw * i / max(1, n - 1)

        def sy(v, _base=base, _ymax=ymax):
            return _base - plot_h * v / (_ymax or 1)

        parts.append(S.text(gx, gy + lab_h, name, T.SIZE["label"], T.GRAY[1]))
        # 末值贴在名字同一行右端：小格里没有第二行的余量
        parts.append(S.text(gx + pw, gy + lab_h, fmt(vs[-1], dec) + unit,
                            T.SIZE["value"], T.GRAY[0], T.WEIGHT["value"],
                            anchor="end"))
        # 独立标度时必须把各自的量程写出来，否则读者会误以为格间可比
        if not shared_scale:
            parts.append(S.text(gx, base + T.SIZE["source"] + 1,
                                f"峰值 {fmt(max(vs), dec)}{unit}", T.SIZE["source"],
                                T.GRAY[3]))

        parts.append(S.line(gx, base, gx + pw, base, T.GRAY[6], T.STROKE["hairline"]))
        # 共享标度下画一条全局参考线，让「这一格离整体最高点多远」看得见
        if shared_scale:
            parts.append(S.line(gx, sy(ymax_shared), gx + pw, sy(ymax_shared),
                                T.GRAY[6], T.STROKE["hairline"], dash="1.5 1.5"))

        d = "M" + " L".join(f"{T.px(sx(i))} {T.px(sy(v))}"
                            for i, v in enumerate(vs))
        parts.append(S.path(d, T.GRAY[1], T.STROKE["data"], cap="round"))
        parts.append(S.circle(sx(n - 1), sy(vs[-1]), T.DOT["r"] * 0.9, T.GRAY[0]))

        # x 轴标签挂在每一列最下面那格，而不是「末行」——末行往往不满，
        # 按末行判会让右边几列一个标签都没有。只标首尾：小倍数靠重复
        # 形状读，不靠查数。
        if pi + cols >= npanel:
            for i, anchor in ((0, "start"), (n - 1, "end")):
                parts.append(S.text(sx(i), base + 3 + T.SIZE["label"], x_labels[i],
                                    T.SIZE["label"], T.GRAY[3], anchor=anchor))

    scale_note = (f"各格共享纵轴 0–{num(ymax_shared, unit)}" if shared_scale
                  else "各格纵轴独立，格间高度不可比")
    H = top + rows * ph + 4 + T.GAP["plot_source"] + T.SIZE["source"]
    body = "\n".join(parts)
    src = f"{source} · {scale_note}" if source else scale_note
    return S.canvas(W, H, body, title, subtitle, src)
