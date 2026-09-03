# -*- coding: utf-8 -*-
"""演示数据工具。

硬规则：演示数据必须确定性。同一份代码任何时候跑出来必须长一样——
否则文档里的预览图和读者跑出来的对不上，图型迭代时也没法比较改动效果。
禁用 random 模块。
"""
import math


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
    lo, hi = min(xs), max(xs)
    if bins is None:
        bins = max(5, min(14, int(len(xs) ** 0.5)))
    edges = nice_ticks(lo, hi, bins)
    counts = [0] * (len(edges) - 1)
    for v in xs:
        k = 0
        while k < len(counts) - 1 and v >= edges[k + 1]:
            k += 1
        counts[k] += 1
    return edges, counts
