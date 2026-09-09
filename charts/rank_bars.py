# -*- coding: utf-8 -*-
"""R1 定序条 · 少类目排名比较（≤10 项）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S
from charts._data import require, require_nonneg


# ════ R1 定序条 ════
# 数据形状：类目 → 单一数值，需要读出高低次序
# 版心：single / a4body（窄栏尤其合适——标签在上，不吃图形宽度）
# 失效：>10 项改用 R3 点阵瀑布；有正负改用 R2 分岔条
# 类目上限随栏宽变：窄栏里每行是「标签在上、条在下」两行高，8 项就顶到
# 一页图该有的高度了；宽栏才放得下 12 项。catalog 声明了这两个数，
# 声明了就必须由代码兜住——写在文档里等人记得，就是迟早会漂的那种约定。
MAX_CATS_NARROW = 8
MAX_CATS_WIDE = 12


def rank_bars(data, title=None, subtitle=None, source=None,
              column="single", unit="", show_value=True):
    """data: [(类目, 数值), ...]，按传入顺序绘制（调用方负责排序）。"""
    require(data, "R1 定序条")
    narrow = T.COLUMN[column] <= T.COLUMN["onehalf"]
    cap = MAX_CATS_NARROW if narrow else MAX_CATS_WIDE
    if len(data) > cap:
        raise ValueError(
            f"R1 定序条在{'窄栏' if narrow else '宽栏'}（{column}）最多 {cap} 项，"
            f"收到 {len(data)} 项。中文类目名不能缩写，再多要么压字要么把图拉成"
            f"跨页的长条——换宽栏，或改用 R3 点阵瀑布。")
    require_nonneg(data, "R1 定序条")

    W = T.COLUMN[column]
    x0, x1 = T.PAD["left"], W - T.PAD["right"]

    lab_h = T.SIZE["label"]
    bar_h = 4.5          # 细条：印刷上细条+留白是编辑语言，粗条是 dashboard 语言
    row_gap = 9.0
    row_h = lab_h + 3.0 + bar_h + row_gap

    top = S.head_height(title, subtitle, W)
    plot_h = row_h * len(data) - row_gap
    H = top + plot_h + T.GAP["plot_source"] + T.SIZE["source"] + 6

    vmax = max(v for _, v in data) or 1
    # 数值跟在条端走，所以量程要给最长那条的数值留出位置，否则出血。
    longest = max(S.text_width(f"{v:,g}{unit}", T.SIZE["value"]) for _, v in data)
    span = (x1 - x0) - longest - 5

    parts = [S.line(x0, top - 2, x0, top + plot_h, T.GRAY[4], T.STROKE["rule"])]  # 零点基线

    for i, (name, v) in enumerate(data):
        y = top + i * row_h
        # 明度即数据：第一名最黑，沿 ladder 递减，地板停在 GRAY[3]——
        # 再浅在胶印上就和网格线分不开了。
        ink = T.GRAY[min(i, 3)]
        bw = span * v / vmax                       # 长度 ∝ 数值，不断轴

        parts.append(S.text(x0 + 1.5, y + lab_h,
                            S.ellipsize(name, x1 - x0 - 4, T.SIZE["label"]),
                            T.SIZE["label"], T.GRAY[2]))
        by = y + lab_h + 3.0
        parts.append(S.rect(x0, by, bw, bar_h, ink))
        if show_value:
            # 数值贴条端，和条一体；不右对齐到栏边，省掉一次视线长途跋涉。
            parts.append(S.text(x0 + bw + 4, by + bar_h - 0.3, f"{v:,g}{unit}",
                                T.SIZE["value"], ink, T.WEIGHT["value"]))
    return S.canvas(W, H, "\n".join(parts), title, subtitle, source)
