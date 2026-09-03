# -*- coding: utf-8 -*-
"""反例：故意违反印刷规范，用来确认校验器没有被改弱。

每一条对应校验器的一条规则；期望的命中条数写在 EXPECT 里，
少一条就说明某条规则失效了。
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S

EXPECT = 8


def build():
    body = "\n".join([
        # 1 中文字号低于 CJK 下限
        f'<text x="6" y="40" font-size="6" fill="{T.GRAY[0]}" font-family="{T.FONT_SANS}">同比增速</text>',
        # 2 文字用了填充档灰 / 3 对纸对比度不足
        f'<text x="6" y="60" font-size="8" fill="{T.GRAY[6]}" font-family="{T.FONT_SANS}">环比</text>',
        # 4 线宽低于印刷地板
        '<line x1="6" y1="70" x2="200" y2="70" stroke="#1F1F1F" stroke-width="0.2"/>',
        # 5 文本出血
        f'<text x="200" y="90" font-size="9" fill="{T.GRAY[0]}" font-family="{T.FONT_SANS}">这是一段会冲出版心右边界的很长的中文说明文字</text>',
        # 6 字体栈缺 CJK 兜底
        '<text x="6" y="110" font-size="9" fill="#1F1F1F" font-family="Inter,sans-serif">缺兜底</text>',
        # 7 深底上的深字，对比度不足
        f'<rect x="6" y="118" width="60" height="14" fill="{T.GRAY[1]}"/>',
        f'<text x="10" y="128" font-size="8" fill="{T.GRAY[0]}" data-on="{T.GRAY[1]}" font-family="{T.FONT_SANS}">深底深字</text>',
        # 8 声明的底色块盖不住文字
        f'<rect x="6" y="136" width="18" height="12" fill="{T.GRAY[0]}"/>',
        f'<text x="15" y="144" font-size="7.5" fill="{T.PAPER}" data-on="{T.GRAY[0]}" '
        f'data-on-box="6,136,18,12" text-anchor="middle" font-family="{T.FONT_SANS}">四个汉字</text>',
    ])
    return S.canvas(T.COLUMN["single"], 158, body, "反例", "故意违规")


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    with open("out/_badcase.svg", "w", encoding="utf-8") as f:
        f.write(build())
    print("out/_badcase.svg")
