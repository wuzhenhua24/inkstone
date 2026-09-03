# -*- coding: utf-8 -*-
"""色彩数学：sRGB ↔ CIELAB，色盲模拟。纯标准库。

这一层存在的唯一理由是让彩色档可以**按 L\\* 定色**而不是按感觉挑色。
按感觉挑出来的色板，影印成黑白就糊成一团——而研报和期刊大量被
黑白影印、传真、激光打印。
"""
import math

# D65 白点
WX, WY, WZ = 0.95047, 1.0, 1.08883

_M = ((0.4124564, 0.3575761, 0.1804375),
      (0.2126729, 0.7151522, 0.0721750),
      (0.0193339, 0.1191920, 0.9503041))
_MI = ((3.2404542, -1.5371385, -0.4985314),
       (-0.9692660, 1.8760108, 0.0415560),
       (0.0556434, -0.2040259, 1.0572252))


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_linear(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def linear_to_hex(rgb):
    out = ""
    for c in rgb:
        v = max(0, min(255, round(_gam(max(0.0, min(1.0, c))) * 255)))
        out += f"{v:02X}"
    return "#" + out


def in_gamut(rgb, eps=1e-4):
    return all(-eps <= c <= 1 + eps for c in rgb)


def lab_to_linear(L, a, b):
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    def f(t):
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787
    x, y, z = f(fx) * WX, f(fy) * WY, f(fz) * WZ
    return tuple(sum(_MI[i][j] * v for j, v in enumerate((x, y, z))) for i in range(3))


def linear_to_lab(rgb):
    x, y, z = (sum(_M[i][j] * v for j, v in enumerate(rgb)) for i in range(3))
    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x / WX), f(y / WY), f(z / WZ)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def lstar(hexcolor):
    return linear_to_lab(hex_to_linear(hexcolor))[0]


def at_lstar(hue_deg, L, chroma_max=60):
    """在给定色相上取明度恰为 L 的颜色，彩度取该明度下能落入色域的最大值。

    这是整个彩色档的支点：色相变，L\\* 不变——于是影印成灰度后，
    彩色图和 mono 图是同一张。
    """
    h = math.radians(hue_deg)
    lo, hi = 0.0, float(chroma_max)
    for _ in range(40):
        mid = (lo + hi) / 2
        rgb = lab_to_linear(L, mid * math.cos(h), mid * math.sin(h))
        if in_gamut(rgb):
            lo = mid
        else:
            hi = mid
    return linear_to_hex(lab_to_linear(L, lo * math.cos(h), lo * math.sin(h)))


# 色盲模拟：Machado 等 2009，重度（severity 1.0），作用于线性 RGB
CVD = {
    "protanopia": ((0.152286, 1.052583, -0.204868),
                   (0.114503, 0.786281, 0.099216),
                   (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968),
                     (0.280085, 0.672501, 0.047413),
                     (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779),
                   (-0.078411, 0.930809, 0.147602),
                   (0.004733, 0.691367, 0.303900)),
}


def simulate(hexcolor, kind):
    rgb = hex_to_linear(hexcolor)
    m = CVD[kind]
    return linear_to_hex(tuple(sum(m[i][j] * rgb[j] for j in range(3))
                               for i in range(3)))
