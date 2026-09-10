# -*- coding: utf-8 -*-
"""例二 · 期刊口吻：各区域预期寿命分布 —— D3 五数摘要

── 选型（至少比较 3 个候选并写下淘汰理由）──
数据形状：5 个组，每组几十个国家各一个数值，关心的是组间分布位置的差别。
载体：期刊单栏配图，会被黑白影印。

  · D3 五数摘要 ← 采用。要读的是「组与组的分布差在哪」，中位数和四分位距
                正好承载这个问题；每组几十个国家，逐点画反而糊。
  · D2 蜂群     —— 淘汰。它适合 40–180 个点、要看到每一条记录的场合。
                这里 208 个国家超出上限，而且读者并不关心具体哪个国家落在哪，
                关心的是区域之间的位置差。
  · M2 散点带回归 —— 淘汰，而且是**用数据淘汰的**：本来想画「人均 GDP vs
                预期寿命」，实测皮尔逊 r 只有 0.620，取对数后才到 0.855——
                这是条 Preston 曲线，在原始横轴上拟合一条直线属于
                SKILL.md 第四节该拒绝的那类图。M2 目前只做线性拟合，
                那就不该用它；换图，而不是把非线性的数据硬塞进线性的图。

北美（n=3）与南亚（n=6）已剔除：3 个点算不出有意义的四分位距，
SKILL.md 第四节写的是「数据撑不起所选图型 → 降级并说明」，这里的说明
就写在副题和来源行里。
"""
from _shared import rows, emit
from charts.tick_box import tick_box
from charts._data import quantile

CN = {"Europe & Central Asia": "欧洲与中亚",
      "Middle East, North Africa, Afghanistan & Pakistan": "中东与北非",
      "Latin America & Caribbean ": "拉美与加勒比",
      "East Asia & Pacific": "东亚与太平洋",
      "Sub-Saharan Africa ": "撒南非洲"}
MIN_N = 10                      # 小于这个样本量算不出可信的四分位距

data, src = rows("life-expectancy-2023.csv")
buckets = {}
for r in data:
    buckets.setdefault(r["region_en"], []).append(float(r["years"]))

groups = [(CN[k], sorted(v)) for k, v in buckets.items()
          if k in CN and len(v) >= MIN_N]
groups.sort(key=lambda g: -quantile(g[1], .5))

dropped = sorted(k for k, v in buckets.items() if len(v) < MIN_N)
# 中位数必须和图里那根中位线用同一个函数算。tick_box 走 quantile()
# 的线性插值，这里若图省事写 vs[len//2]，偶数样本下两者会差半档——
# 标题声称的数字和图上画的不是同一个数，是最难被发现的那种错。
gap = quantile(groups[0][1], .5) - quantile(groups[-1][1], .5)

svg = tick_box(
    groups,
    # 标题按实测宽度选过：完整表述「撒南非洲的预期寿命中位数比欧洲与中亚
    # 低 15.7 岁」是 242.5pt，超出单栏可用的 228.9pt，折行后会剩一个「岁」
    # 字孤悬。主语和量级留在标题里，「预期寿命 / 中位数」交给副题。
    title=f"{groups[-1][0]}比{groups[0][0]}低 {gap:.1f} 岁",
    subtitle="出生时预期寿命中位数 · 2023 年 · 单位：岁 · 箱体为四分位距",
    source=f"数据来源：世界银行 WDI · SP.DYN.LE00.IN · "
           f"已剔除样本不足 {MIN_N} 国的{'、'.join(('北美', '南亚'))}",
    unit="岁", column="single")

if __name__ == "__main__":
    print(f"  （已剔除 {len(dropped)} 个样本不足的区域：{dropped}）")
    emit(svg, "ex2-life-expectancy")
