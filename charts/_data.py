# -*- coding: utf-8 -*-
"""演示数据工具。

硬规则：演示数据必须确定性。同一份代码任何时候跑出来必须长一样——
否则文档里的预览图和读者跑出来的对不上，图型迭代时也没法比较改动效果。
禁用 random 模块。
"""
import math
import unicodedata


# ─────────────────────────────────────────────────────────────
# 入参守卫。七道类目上限都会给出改图建议，空数据和负值没理由待遇更差：
# 裸 max() 抛的「max() arg is an empty sequence」对用户毫无意义，
# 而负值在长度编码的图里会被 max(w,0) 悄悄吞成零长条——那是错图不是报错。
# ─────────────────────────────────────────────────────────────

def require(rows, code, what="数据"):
    """空输入当场拒绝。空图不是图，静默画出一张空白版心更糟。"""
    if not rows:
        raise ValueError(f"{code} 收到空{what}，画不出图。至少给一项。")
    return rows


def require_nonneg(pairs, code, alt="R2 分岔条"):
    """长度 / 个数 / 面积 ∝ 数值的图不接受负值。

    pairs: [(名字, 数值), ...]。这类图的几何是从零点单向长出来的，
    负值没有对应的画法：条会被 max(w,0) 吞成零长，跟在条端的数值
    则跑到纸外；百格方阵更狠，负值会让格数变成 165。
    与其画一张撒谎的图，不如指回真正承载正负的图型。
    """
    neg = [(n, v) for n, v in pairs if v < 0]
    if neg:
        shown = "、".join(f"{n}={num(v)}" for n, v in neg[:3])
        more = f" 等 {len(neg)} 项" if len(neg) > 3 else ""
        raise ValueError(
            f"{code} 是从零点单向长出来的图，不接受负值：{shown}{more}。"
            f"长度不可能 ∝ 负数——改用 {alt}。")
    return pairs


def rnd(i, k=0):
    """确定性伪随机 [0, 1)。同 (i, k) 永远返回同一个值。"""
    x = math.sin(i * 127.1 + k * 311.7) * 43758.5453
    return x - math.floor(x)


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def nice_ticks(lo, hi, n=6):
    """把 [lo, hi] 切成人读得懂的刻度（1/2/5 × 10^k）。

    返回的首尾刻度会包住整个数据范围——调用方应当把标度域撑到
    ticks[0]..ticks[-1]，而不是把域外刻度裁掉。裁掉的结果是轴上
    只剩中间两个数字，读者不知道量程从哪开始。
    """
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / max(1, n)
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=10) * mag
    v = math.floor(lo / step) * step
    out = []
    while v < hi - step * 1e-9:
        out.append(round(v, 10))
        v += step
    out.append(round(v, 10))
    return out


def quantile(xs, q):
    """线性插值分位数（与 numpy 默认的 type 7 一致）。"""
    s = sorted(xs)
    if len(s) == 1:
        return float(s[0])
    pos = (len(s) - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def five_number(xs, whisker=1.5):
    """五数概括 + 异常值（1.5 IQR 规则）。

    须线止于「最远的非异常值」，不是止于 Q1/Q3±1.5IQR 那个计算值——
    后者会画出一条并不存在的数据端点。
    """
    q1, med, q3 = quantile(xs, .25), quantile(xs, .5), quantile(xs, .75)
    iqr = q3 - q1
    lof, hif = q1 - whisker * iqr, q3 + whisker * iqr
    inl = [v for v in xs if lof <= v <= hif]
    return {"q1": q1, "med": med, "q3": q3, "n": len(xs),
            "lo": min(inl) if inl else q1, "hi": max(inl) if inl else q3,
            "outliers": sorted(v for v in xs if v < lof or v > hif)}


def decimals_for(vals, eps=0.05):
    """一组数该保留几位小数：有一个带小数，全组就都带。

    `:g` 会把 95.0 写成「95」而把 99.8 写成「99.8」，同一格网格里
    小数位参差不齐，读者会以为精度不同。
    """
    return 1 if any(abs(v - round(v)) > eps for v in vals) else 0


def num(v, unit="", decimals=None):
    """数值的印刷写法。**永不走科学计数法。**

    `f"{v:,g}"` 在 |v| ≥ 1e6 时会切到科学计数法：营收 1234567 印成
    「1.23457e+06」。这在研报和期刊里是当场作废的一张图，而校验器
    判不出来——那是一段完全合法的文字，字号、字色、宽度全部合规，
    只有读者知道它没法读。这个项目最怕的就是这一类：**不报错的错图。**

    decimals 显式传入时按位数补零（同一组数要对齐小数位，见 decimals_for）；
    不传则按量级自动定三位有效数字，并去掉尾随的零。
    """
    auto = decimals is None
    if auto:
        a = abs(v)
        if a == 0:
            decimals = 0
        else:
            # 和 `:g` 同样的六位有效数字——**唯一的差别是绝不切到科学计数法**。
            # 有效位数写少一点看着更清爽，但那会顺手抹掉真实精度：中位数
            # 189.5 印成「190」、106.5 印成「106」（half-even 还让两者
            # 往不同方向倒）。这个函数的职责是修科学计数法，不是替调用方
            # 决定精度——要少几位，显式传 decimals。
            decimals = min(12, max(0, 5 - int(math.floor(math.log10(a)))))
    s = f"{v:,.{decimals}f}"
    if auto and "." in s:
        s = s.rstrip("0").rstrip(".")
    return s + _unit_gap(unit) + unit


# 数量级词是数字的一部分，紧贴：14.5亿、3,200万。
# 量词是另一个词，要留空：1,840 件、31.5 分钟、150 天。
# 拉丁与符号单位按拉丁惯例紧贴：23.8%、12kg。
_MAGNITUDE = "万亿千百兆"


def _unit_gap(unit):
    """数字和单位之间要不要留一个空格。

    这条规则此前根本不存在，是裸拼接——于是**同一行来源里**会同时出现
    「箱宽 5分钟」和「10 箱」（d1-step-histogram 实测），同一张图里出现
    「14.5亿」和「比中国多 4,196 万」。一个把间隔号量到 0.278em vs 1.000em
    的项目，却没给数字↔汉字的边界定规则，是唯一一处自己拆自己台的地方。

    留空与否不是一刀切：万/亿/千是数量级词，读者把「14.5亿」当一个数读，
    中间插空格反而把它掰成两半；而「件」「分钟」「天」是量词，是数字之后
    的另一个词，不留空就挤在一起。
    """
    if not unit:
        return ""
    head = unit[0]
    if head in _MAGNITUDE:
        return ""
    return " " if unicodedata.east_asian_width(head) in ("W", "F") else ""


def fmt(v, decimals=0):
    return f"{v:,.{decimals}f}"


def linreg(xs, ys):
    """最小二乘直线 + 皮尔逊 r。返回 (斜率, 截距, r)。"""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    r = sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0
    return slope, my - slope * mx, r


def histogram(xs, bins=None):
    """等宽分箱。箱边取人读得懂的整数，不是 min/max 直接均分——
    「12.37–19.84」这种箱标签没人愿意读。返回 (箱边, 各箱计数)。"""
    require(xs, "D1 阶梯直方", "样本")
    lo, hi = min(xs), max(xs)
    if bins is None:
        bins = max(5, min(14, int(len(xs) ** 0.5)))
    edges = nice_ticks(lo, hi, bins)
    # 全等值（含单点样本）时 nice_ticks 只给得出一个边，切不出箱。
    # 这是合法输入——「所有人耗时都是 5 分钟」是一条真实的分布——
    # 所以给一个量级相称的单箱，而不是让 counts[k] 抛 IndexError。
    if len(edges) < 2:
        half = abs(lo) * 0.05 or 0.5
        return [lo - half, lo + half], [len(xs)]
    counts = [0] * (len(edges) - 1)
    for v in xs:
        k = 0
        while k < len(counts) - 1 and v >= edges[k + 1]:
            k += 1
        counts[k] += 1
    return edges, counts
