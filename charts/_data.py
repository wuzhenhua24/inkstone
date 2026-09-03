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
