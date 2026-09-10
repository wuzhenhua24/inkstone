# -*- coding: utf-8 -*-
"""例一 · 研报口吻：人口排名 —— R1 定序条

── 选型（SKILL.md 第一节要求至少比较 3 个候选并写下淘汰理由）──
数据形状：8 个类目 → 各一个数值，要读出高低次序。载体：券商研报正文，
A4 单栏配图，读者会在正文里找到「谁第一」这句话对应的图。

  · R1 定序条  ← 采用。类目 ≤8、单一数值、要读次序，正是它的数据形状；
                窄栏里「标签在上、条在下」不吃图形宽度，中文国名不用缩写。
  · R3 点阵瀑布 —— 淘汰。它编码「可数的整数量」，一个点代表几千万人时，
                读者会去数点，而人口不是一件件数出来的东西；catalog 的
                失效条件写的就是「数值不可数 → R1」。
  · C1 百格方阵 —— 淘汰。它回答「占比构成」，这里的问题是排名不是构成；
                而且前 12 名只占世界人口的六成，画成百格等于宣称它是全体。

单位取「亿人」而不是原始的 14.5 亿这个整数：图上印 1,450,935,791
没有任何读者受得了，副题写清单位是中文图表的常规做法。
"""
from _shared import rows, emit
from charts.rank_bars import rank_bars

CN = {"India": "印度", "China": "中国", "United States": "美国",
      "Indonesia": "印度尼西亚", "Pakistan": "巴基斯坦", "Nigeria": "尼日利亚",
      "Brazil": "巴西", "Bangladesh": "孟加拉国"}

data, src = rows("population-2024.csv")
top = [r for r in data if r["name_en"] in CN][:8]
pairs = [(CN[r["name_en"]], int(r["population"]) / 1e8) for r in top]

lead = (int(top[0]["population"]) - int(top[1]["population"])) / 1e4

svg = rank_bars(
    pairs,
    title=f"印度人口居首，比中国多 {lead:,.0f} 万",
    subtitle="2024 年 · 单位：亿人 · 人口前八的经济体",
    source="数据来源：世界银行 WDI · SP.POP.TOTL · 2026-09-10 取数",
    unit="亿", column="single")

if __name__ == "__main__":
    emit(svg, "ex1-population")
