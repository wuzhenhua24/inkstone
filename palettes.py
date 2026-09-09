# -*- coding: utf-8 -*-
"""彩色档。

**核心约束：色相可以换，L\\* 不能换。**

每套色板都是把 tokens.GRAY 的七级明度原样搬到某个色相上——所以
彩色图影印成黑白之后，和 mono 版本是同一张图。研报和期刊大量被
黑白影印、传真、激光打印，色板若不守这条，出版环节就会毁掉它。

同时这条约束顺带解决了色盲安全：单色相 + 明度阶梯，本来就不依赖
色相辨别。需要区分类目时用直接标注（见 S2 细线族），不靠色相。
彩度整体压低，是为了印刷上不刺眼、也为了留出网点空间。
"""
from charts._color import at_lstar, lstar

# GRAY 的七级明度。彩色档必须逐级对齐这些值。
LADDER = [12, 25, 37, 49, 62, 76, 88]

PRESETS = {
    "mono":    {"cn": "墨灰", "hue": None, "chroma": 0},
    "indigo":  {"cn": "靛青", "hue": 268, "chroma": 24},
    "ochre":   {"cn": "赭石", "hue": 58,  "chroma": 30},
    "celadon": {"cn": "青瓷", "hue": 178, "chroma": 20},
}


def build(name):
    """返回该色板的七级阶梯，明度逐级等于 LADDER。"""
    if name not in PRESETS:
        raise ValueError(f"没有名为 {name} 的色板。可选：{', '.join(PRESETS)}")
    p = PRESETS[name]
    if p["hue"] is None:
        return None                      # mono 用 tokens 里原本的灰阶
    return [at_lstar(p["hue"], L, p["chroma"]) for L in LADDER]


def audit(name):
    """返回该色板的问题清单。空列表表示合格。"""
    from charts._color import simulate
    fails = []
    ramp = build(name)
    if ramp is None:
        return fails
    for i, (c, want) in enumerate(zip(ramp, LADDER)):
        got = lstar(c)
        if abs(got - want) > 1.0:
            fails.append(f"{name}[{i}]={c} 明度 {got:.1f}，应为 {want}——"
                         f"影印成灰度后会和 mono 版对不上")
    for kind in ("protanopia", "deuteranopia", "tritanopia"):
        sim = [simulate(c, kind) for c in ramp]
        for i in range(len(sim) - 1):
            d = abs(lstar(sim[i]) - lstar(sim[i + 1]))
            if d < 10:
                fails.append(f"{name} 在 {kind} 下第 {i}/{i+1} 级只差 {d:.1f} L*")
    return fails
