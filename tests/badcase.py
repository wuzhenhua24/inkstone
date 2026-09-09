# -*- coding: utf-8 -*-
"""反例：故意违反印刷规范，用来确认校验器没有被改弱。

每一条对应校验器的一条规则；期望的命中条数写在 EXPECT 里，
少一条就说明某条规则失效了。
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S

EXPECT = 11


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
        # 9 两个只差 4.6 L* 的灰，中间故意夹一个第三色。
        #   校验器若只比「文档里前后相邻的两个」，这一条就整个逃掉——
        #   同样三个颜色换个发射顺序结论就翻，那是运气不是判定。
        #   分隔色必须是全篇首次出现的色值：用前面已经出现过的色（比如
        #   GRAY[0]）当分隔是没用的，去重之后两个近灰照样贴在一起，
        #   旧规则依然抓得到，这条反例就没有牙齿了。
        '<rect x="6" y="154" width="40" height="10" fill="#8A8A8A"/>',
        f'<rect x="50" y="154" width="40" height="10" fill="{T.GRAY[5]}"/>',
        '<rect x="94" y="154" width="40" height="10" fill="#969696"/>',
        # 10 同一基线上的两段文字互相压字。
        #    x 轴标签按字符数估宽抽稀时就是这个下场：中西混排下
        #    「till」字符最多而「环比增速」最宽，按字符数留位欠 21pt。
        f'<text x="6" y="178" font-size="7.5" fill="{T.GRAY[0]}" font-family="{T.FONT_SANS}">环比增速</text>',
        f'<text x="20" y="178" font-size="7.5" fill="{T.GRAY[0]}" font-family="{T.FONT_SANS}">同比增速</text>',
    ])
    # 11 四件套缺来源行：canvas 的第四个参数留空。图题和副题都在，
    #    唯独没有来源行——读者无从判断这些数字是哪来的、样本多大。
    #    SKILL.md 第三节写的是「缺一返工」，那就必须能判，不能只写在文档里。
    return S.canvas(T.COLUMN["single"], 196, body, "反例", "故意违规")


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    with open("out/_badcase.svg", "w", encoding="utf-8") as f:
        f.write(build())
    print("out/_badcase.svg")
