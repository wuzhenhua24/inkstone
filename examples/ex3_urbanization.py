# -*- coding: utf-8 -*-
"""例三 · 政企汇报口吻：城镇化率三十三年 —— S2 细线族

── 选型（至少比较 3 个候选并写下淘汰理由）──
数据形状：5 个实体各一条 34 年的序列，要读的是「谁涨得快、谁在什么时候
交叉」。载体：汇报文档跨栏大图（double，170mm）。

  · S2 细线族   ← 采用。3–6 条序列同轴比较正是它的形状；这里要读交叉
                （中国 2010 年前后越过尼日利亚），同轴才看得见。
  · S3 小倍数网格 —— 淘汰。它把每条序列拆进各自的格子，各看各的趋势很清楚，
                但**读不出交叉**——而交叉恰恰是这张图要讲的事。
                catalog 的失效条件写的就是「≤6 条且要读交叉 → S2」。
  · S1 日序条码 —— 淘汰。它是单序列、每天一个读数的图，这里是 5 条年度序列，
                数据形状根本不匹配。

纵轴从零起：城镇化率是「占总人口的比重」，零点有实义，截断会夸大差距。
"""
from _shared import rows, emit
from charts.line_family import line_family

CN = {"CHN": "中国", "NGA": "尼日利亚", "BRA": "巴西",
      "IND": "印度", "KOR": "韩国"}

data, src = rows("urbanization-1990-2023.csv")
series = {}
for r in data:
    series.setdefault(r["iso3"], {})[int(r["year"])] = float(r["urban_pct"])

years = sorted(series["CHN"])
# 按重要性降序传入：第一条最重（最黑最粗）。这里的「重要性」就是本图的
# 结论——涨得最快的那条。
order = sorted(series, key=lambda k: -(series[k][years[-1]] - series[k][years[0]]))
lines = [(CN[k], [series[k][y] for y in years]) for k in order]

lead = series[order[0]][years[-1]] - series[order[0]][years[0]]

svg = line_family(
    lines,
    [str(y) for y in years],
    title=f"中国城镇化率 {len(years) - 1} 年提高 {lead:.0f} 个百分点，五个经济体中最快",
    subtitle=f"城镇人口占总人口比重 · 单位：% · {years[0]}–{years[-1]}",
    source="数据来源：世界银行 WDI · SP.URB.TOTL.IN.ZS · 2026-09-10 取数",
    unit="%", column="double")

if __name__ == "__main__":
    emit(svg, "ex3-urbanization")
