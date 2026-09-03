# -*- coding: utf-8 -*-
"""最小 SVG 原语 + 中西文混排宽度测量。纯标准库。

中文图表最常见的翻车是标签溢出：按拉丁经验估宽（~0.5em/字符），
碰上汉字实际占 1.0em，估出来的宽度只有真实值的一半，标签就压到
图里去了。这里用 Unicode 东亚宽度属性逐字符量，汉字/全角标点
按 1.0em 计——PingFang、思源黑体这类字体的汉字就是精确 1em 方块，
所以这个测量对 CJK 是准的，对拉丁是保守估计（宁可估宽）。
"""
import unicodedata
from html import escape

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T


# 拉丁字符的平均宽度系数（em）。取偏大值，宁可预留过多空间。
_LATIN_EM = {
    "narrow": 0.30,   # i l j t f r I . , ; : ' " ! | ( ) [ ]
    "normal": 0.56,
    "wide":   0.78,   # m w M W @ % —— 大写和宽字母
}
_NARROW = set("iljtfrI.,;:'\"!|()[]{}·-·")
_WIDE = set("mwMWQGO@%&")


def text_width(s: str, size_pt: float) -> float:
    """返回字符串在给定字号下的估算宽度（pt）。CJK 精确，拉丁保守偏宽。"""
    em = 0.0
    for ch in s:
        w = unicodedata.east_asian_width(ch)
        if w in ("W", "F"):          # 汉字、全角标点、假名
            em += 1.0
        elif ch in _NARROW:
            em += _LATIN_EM["narrow"]
        elif ch in _WIDE:
            em += _LATIN_EM["wide"]
        elif w == "A":               # 歧义宽度（希腊、西里尔），按拉丁算
            em += _LATIN_EM["normal"]
        else:
            em += _LATIN_EM["normal"]
    return em * size_pt


def has_cjk(s: str) -> bool:
    return any(unicodedata.east_asian_width(c) in ("W", "F") for c in s)


def min_size_for(s: str) -> float:
    """这段文本允许的最小字号——含汉字就抬到 CJK 下限。"""
    return T.MIN_CJK_PT if has_cjk(s) else T.MIN_LATIN_PT


def effective_size(s: str, size_pt: float) -> float:
    """text() 实际会用的字号。请求 6.5pt 而文本含汉字时会被抬到 7.5pt，
    此时若还按 6.5 算宽度，折行和出血判断全部偏小 15%。
    凡是算宽度都要先过这一道。"""
    return max(size_pt, min_size_for(s))


def ellipsize(s: str, max_w: float, size_pt: float) -> str:
    """按实际宽度截断并加省略号。中文用全角省略号，西文用 …。"""
    if text_width(s, size_pt) <= max_w:
        return s
    mark = "…"
    mw = text_width(mark, size_pt)
    out = ""
    for ch in s:
        if text_width(out + ch, size_pt) + mw > max_w:
            break
        out += ch
    return out + mark if out else mark


def wrap(s, max_w, size_pt, sep=" · "):
    """按实测宽度折行。优先在「·」分隔处断，装不下再逐字断。

    中文副题要承载口径、单位和时间范围，天生就长，85mm 单栏装不下是
    常态而不是例外——所以折行是内建行为，不是调用方该操心的事。
    截断会丢掉口径，比折行糟得多。
    """
    size_pt = effective_size(s, size_pt)      # 折行必须按生效字号算
    if text_width(s, size_pt) <= max_w:
        return [s]
    segs = s.split(sep)
    lines, cur = [], ""
    for seg in segs:
        cand = seg if not cur else cur + sep + seg
        if text_width(cand, size_pt) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = seg
    if cur:
        lines.append(cur)

    # 单段仍然过宽（比如一个没有分隔符的长句）时逐字断
    out = []
    for ln in lines:
        while text_width(ln, size_pt) > max_w:
            cut = ""
            for ch in ln:
                if text_width(cut + ch, size_pt) > max_w:
                    break
                cut += ch
            out.append(cut)
            ln = ln[len(cut):]
        if ln:
            out.append(ln)
    return out


# ── 元素 ──────────────────────────────────────────────────────

def text(x, y, s, size=T.SIZE["label"], fill=T.INK, weight=None,
         anchor="start", family=None, spacing=None, baseline=None,
         on=None, on_box=None):
    """on: 这段文字坐在什么底色上（深色格里的数字要翻成纸白）。
    on_box: 那块底色的矩形 (x, y, w, h)。

    不传 on 就是坐在纸上。校验器读 data-on 算对比度，读 data-on-box
    确认底色真的盖住了整段文字——白字有一半飘到白纸上，在灰度审阅时
    几乎看不出来，只能靠机器判。
    """
    size = max(size, min_size_for(str(s)))   # 字号地板在这里强制，调用处想违反也违反不了
    a = [f'x="{T.px(x)}"', f'y="{T.px(y)}"', f'font-size="{T.px(size)}"',
         f'fill="{fill}"', f'font-family="{family or T.FONT_SANS}"']
    if weight:   a.append(f'font-weight="{weight}"')
    if anchor != "start": a.append(f'text-anchor="{anchor}"')
    if spacing:  a.append(f'letter-spacing="{spacing}"')
    if on:       a.append(f'data-on="{on}"')
    if on_box:
        a.append('data-on-box="%s"' % ",".join(str(T.px(v)) for v in on_box))
    if baseline: a.append(f'dominant-baseline="{baseline}"')
    a.append('font-variant-numeric="tabular-nums"')
    return f'<text {" ".join(a)}>{escape(str(s))}</text>'


def rect(x, y, w, h, fill=T.INK, rx=0, opacity=None):
    o = f' fill-opacity="{opacity}"' if opacity is not None else ""
    r = f' rx="{rx}"' if rx else ""
    return (f'<rect x="{T.px(x)}" y="{T.px(y)}" width="{T.px(max(w,0))}" '
            f'height="{T.px(max(h,0))}" fill="{fill}"{r}{o}/>')


def line(x1, y1, x2, y2, stroke=T.RULE, width=T.STROKE["rule"], dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{T.px(x1)}" y1="{T.px(y1)}" x2="{T.px(x2)}" y2="{T.px(y2)}" '
            f'stroke="{stroke}" stroke-width="{T.px(width)}"{d}/>')


def path(d, stroke=T.INK, width=T.STROKE["data"], fill="none", cap="butt"):
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{T.px(width)}" stroke-linecap="{cap}"/>')


def circle(cx, cy, r, fill=T.INK, opacity=None):
    o = f' fill-opacity="{opacity}"' if opacity is not None else ""
    return f'<circle cx="{T.px(cx)}" cy="{T.px(cy)}" r="{T.px(r)}" fill="{fill}"{o}/>'


# ── 画布 ──────────────────────────────────────────────────────

def canvas(width_pt, height_pt, body, title=None, subtitle=None, source=None):
    """组装整张图。四件套固定：图题 + 副题（图例/口径）+ 图 + 来源行。

    宽高单位是 pt 并写进 width/height 属性，导出 PDF 时 1:1 落纸。
    """
    avail = width_pt - T.PAD["left"] - T.PAD["right"]
    head = []
    y = T.PAD["top"] + T.SIZE["title"]
    if title:
        for ln in wrap(title, avail, T.SIZE["title"]):
            head.append(text(T.PAD["left"], y, ln, T.SIZE["title"],
                             T.INK, T.WEIGHT["title"]))
            y += T.SIZE["title"] * 1.32
        y += T.GAP["title_sub"] - T.SIZE["title"] * 1.32 + T.SIZE["subtitle"]
    if subtitle:
        for ln in wrap(subtitle, avail, T.SIZE["subtitle"]):
            head.append(text(T.PAD["left"], y, ln, T.SIZE["subtitle"], T.MUTED))
            y += T.SIZE["subtitle"] * 1.35

    # 来源行同样会超长（图型会往里追加口径、n、r、标度注记）。
    # 调用方按「一行」算高度，多出来的行数由这里补进画布——
    # 让每张图各自去算来源行行数，只会漏。
    foot = []
    if source:
        lines = wrap(source, avail, T.SIZE["source"])
        lh = T.SIZE["source"] * 1.4
        height_pt += lh * (len(lines) - 1)
        fy = height_pt - 4 - lh * (len(lines) - 1)
        for ln in lines:
            foot.append(text(T.PAD["left"], fy, ln, T.SIZE["source"],
                             T.SRC, T.WEIGHT["source"], spacing="0.06em"))
            fy += lh

    return f'''<svg xmlns="http://www.w3.org/2000/svg" version="1.1"
     width="{T.px(width_pt)}pt" height="{T.px(height_pt)}pt"
     viewBox="0 0 {T.px(width_pt)} {T.px(height_pt)}">
<rect width="100%" height="100%" fill="{T.PAPER}"/>
{chr(10).join(head)}
{body}
{chr(10).join(foot)}
</svg>'''


def head_height(title=None, subtitle=None, width_pt=None):
    """标题区占用的高度，供图形区计算起始 y。

    传 width_pt 才能算准——标题和副题都可能折行，行数由版心宽度决定。
    """
    avail = (width_pt - T.PAD["left"] - T.PAD["right"]) if width_pt else None
    h = T.PAD["top"]
    if title:
        n = len(wrap(title, avail, T.SIZE["title"])) if avail else 1
        h += T.SIZE["title"] * (1.32 * (n - 1) + 1) + T.GAP["title_sub"]
    if subtitle:
        n = len(wrap(subtitle, avail, T.SIZE["subtitle"])) if avail else 1
        h += T.SIZE["subtitle"] * (1.35 * (n - 1) + 1)
    return h + T.GAP["sub_plot"]
