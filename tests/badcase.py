# 反例：故意违反印刷规范，看校验器抓不抓得住
import sys
sys.path.insert(0, "/Users/zhenhua/Documents/gitpro/inkstone")
import tokens as T
from charts import _svg as S

body = "\n".join([
    f'<text x="6" y="40" font-size="6" fill="{T.GRAY[0]}" font-family="{T.FONT_SANS}">同比增速</text>',
    f'<text x="6" y="60" font-size="8" fill="{T.GRAY[6]}" font-family="{T.FONT_SANS}">环比</text>',
    '<line x1="6" y1="70" x2="200" y2="70" stroke="#1F1F1F" stroke-width="0.2"/>',
    f'<text x="200" y="90" font-size="9" fill="{T.GRAY[0]}" font-family="{T.FONT_SANS}">这是一段会冲出版心右边界的很长的中文说明文字</text>',
    '<text x="6" y="110" font-size="9" fill="#1F1F1F" font-family="Inter,sans-serif">缺兜底</text>',
    # 深底深字：声明了底色，但深字在深底上对比度不足
    f'<rect x="6" y="118" width="60" height="14" fill="{T.GRAY[1]}"/>',
    f'<text x="10" y="128" font-size="8" fill="{T.GRAY[0]}" data-on="{T.GRAY[1]}" font-family="{T.FONT_SANS}">深底深字</text>',
])
open("out/_badcase.svg", "w", encoding="utf-8").write(
    S.canvas(T.COLUMN["single"], 145, body, "反例", "故意违规"))
