# -*- coding: utf-8 -*-
"""测试入口。CI 和本地都跑这一个：python3 tests/run.py

六组检查：
  1 渲染      全部图型能画出来
  2 校验      产物 / token / 目录全部合规
  3 反例      校验器仍然抓得住违规，条数不少于预期
  4 越界      每张有上限的图型都会拒绝超限数据
  4.1 负值    长度编码的图会拒绝负值，而不是画出零长条
  4.2 退化    空数据一律友好拒绝；全等值样本仍要画得出来
  4.3 留位    标签抽稀按实测宽度，退回字符数估宽必须被抓住
  4.4 色板    切色板后原语默认参数必须跟着走，不许漏出 mono 灰
  5 确定性    跑两次字节相同（演示数据不许用随机数）
  5.5 导出    PDF / PNG 真的产出且不是空白页
  6 目录闭环  catalog 里每个编号都有渲染产物
  7 灰度等价  彩色版逐处用色的明度必须与 mono 版一致
"""
import io, os, re, subprocess, sys, contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import tests.badcase as badcase
import tokens as T
from charts import _svg
from scripts.validate import check, check_tokens, check_catalog

fails = []


def group(name):
    print(f"\n── {name} " + "─" * max(0, 46 - len(name)))


def ok(msg):
    print(f"  ✓ {msg}")


def bad(msg):
    print(f"  ✗ {msg}")
    fails.append(msg)


def warn(msg):
    """本地缺依赖时提示，CI 上则判失败——产物导出是这个项目的卖点，
    不能长期处于「从没验证过」的状态。"""
    if os.environ.get("CI"):
        bad(msg)
    else:
        print(f"  ! {msg}")


# 1 · 渲染 ─────────────────────────────────────────────────────
group("渲染")
for script in ("demo.py", "demo_palettes.py"):
    r = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if r.returncode:
        bad(f"{script} 失败：{r.stderr.strip()[:200]}")
    else:
        ok(r.stdout.strip().splitlines()[-1])

svgs = sorted(f for f in os.listdir("out") if f.endswith(".svg")
              and not f.startswith("_"))

# 2 · 校验 ─────────────────────────────────────────────────────
group("校验")
for f in (check_tokens(), check_catalog()):
    for m in f:
        bad(m)
if not check_tokens() and not check_catalog():
    ok("tokens.py 与 catalog.md 自检通过")
n_bad = 0
for name in svgs:
    for m in check(os.path.join("out", name)):
        bad(f"{name}: {m}")
        n_bad += 1
if not n_bad:
    ok(f"{len(svgs)} 份产物全部合规")

# 3 · 反例 ─────────────────────────────────────────────────────
group("反例")
with open("out/_badcase.svg", "w", encoding="utf-8") as fh:
    fh.write(badcase.build())
hits = check("out/_badcase.svg")
if len(hits) < badcase.EXPECT:
    bad(f"反例只命中 {len(hits)} 条，预期 ≥{badcase.EXPECT}——有规则失效了：\n"
        + "\n".join(f"      命中：{h}" for h in hits))
else:
    ok(f"反例命中 {len(hits)} 条（预期 ≥{badcase.EXPECT}）")
os.remove("out/_badcase.svg")

# 4 · 越界防护 ─────────────────────────────────────────────────
group("越界防护")
from charts.hundred_grid import hundred_grid
from charts.beeswarm import beeswarm
from charts.matrix_heat import matrix_heat
from charts.tick_box import tick_box
from charts.line_family import line_family
from charts.small_multiples import small_multiples
from charts.stacked_bands import stacked_bands

GUARDS = [
    ("C1 类目超限", hundred_grid, ([(f"类{i}", 10) for i in range(8)],)),
    ("D2 组数超限", beeswarm, ([(f"组{i}", [1, 2, 3]) for i in range(8)],)),
    ("M1 格数超限", matrix_heat, ([f"行{i}" for i in range(12)],
                                  [f"列{j}" for j in range(10)],
                                  [[1] * 10 for _ in range(12)])),
    ("D3 组数超限", tick_box, ([(f"组{i}", [1, 2, 3, 4]) for i in range(10)],)),
    ("S2 线数超限", line_family, ([(f"线{i}", [1, 2]) for i in range(8)], ["a", "b"])),
    ("S3 格数超限", small_multiples, ([(f"格{i}", [1, 2]) for i in range(14)], ["a", "b"])),
    ("C2 层数超限", stacked_bands, ([(f"层{i}", [1, 2]) for i in range(7)], ["a", "b"])),
]
leaked = 0
for label, fn, args in GUARDS:
    try:
        fn(*args, title="越界")
        bad(f"{label} 未被拦下")
        leaked += 1
    except ValueError:
        pass
if not leaked:
    ok(f"{len(GUARDS)} 道上限全部生效")

# 4.1 · 负值防护 ───────────────────────────────────────────────
# 长度 / 个数 / 面积 ∝ 数值的图收到负值时，几何没有对应的画法：
# 条被 max(w,0) 吞成零长、跟在条端的数值跑到纸外、百格方阵分出 165 格。
# 画一张撒谎的图比报错糟得多，所以这些必须当场拒绝。
group("负值防护")
from charts.rank_bars import rank_bars
from charts.diverging_bars import diverging_bars
from charts.dot_cascade import dot_cascade
from charts.day_series import day_series
from charts.scatter_fit import scatter_fit
from charts.step_histogram import step_histogram
from datetime import date, timedelta

_d0 = date(2026, 4, 1)
NEG = [
    ("R1 负值", rank_bars,       ([("甲", 5), ("乙", -3)],)),
    ("R3 负值", dot_cascade,     ([("甲", 5), ("乙", -3)],)),
    ("C1 负值", hundred_grid,    ([("甲", 50), ("乙", -20)],)),
    ("S1 负值", day_series,      ([(_d0 + timedelta(days=i), -1 if i == 5 else 100)
                                  for i in range(70)],)),
    ("S3 负值", small_multiples, ([("甲", [1, -2])], ["a", "b"])),
    ("C2 负值", stacked_bands,   ([("甲", [5, 4]), ("乙", [-3, 2])], ["1月", "2月"])),
    ("S2 负值+零起点", line_family, ([("甲", [1, -2])], ["a", "b"])),
]
leaked = 0
for label, fn, args in NEG:
    try:
        fn(*args, title="负值")
        bad(f"{label} 未被拦下——画出了一张长度不 ∝ 数值的图")
        leaked += 1
    except ValueError:
        pass
# R2 分岔条的职责就是承载正负，它必须照画不误
try:
    diverging_bars([("甲", 5), ("乙", -3)], title="正负")
except ValueError as e:
    bad(f"R2 分岔条被误拦：{e}")
    leaked += 1
if not leaked:
    ok(f"{len(NEG)} 张拒绝负值，R2 分岔条照画不误")

# 4.2 · 退化输入 ───────────────────────────────────────────────
# 空数据抛裸的「max() arg is an empty sequence」对用户毫无意义；
# 七道类目上限都给了改图建议，空数据没理由待遇更差。
group("退化输入")
EMPTY = [
    ("R1", rank_bars, ([],)),               ("R2", diverging_bars, ([],)),
    ("R3", dot_cascade, ([],)),             ("S1", day_series, ([],)),
    ("S2", line_family, ([], [])),          ("S2 空序列", line_family, ([("甲", [])], [])),
    ("S3", small_multiples, ([], [])),      ("C1", hundred_grid, ([],)),
    ("C2", stacked_bands, ([], [])),        ("D1", step_histogram, ([],)),
    ("D2", beeswarm, ([],)),                ("D2 空组", beeswarm, ([("甲", [])],)),
    ("D3", tick_box, ([],)),                ("D3 空组", tick_box, ([("甲", [])],)),
    ("M1", matrix_heat, ([], [], [])),      ("M2", scatter_fit, ([],)),
]
raw = 0
for label, fn, args in EMPTY:
    try:
        fn(*args, title="空")
        bad(f"{label} 空数据被静默画出来了——空图不是图")
        raw += 1
    except ValueError as e:
        if "empty sequence" in str(e):
            bad(f"{label} 空数据抛的还是裸 max()/min()：{e}")
            raw += 1
    except Exception as e:
        bad(f"{label} 空数据抛了 {type(e).__name__}，应当是带解释的 ValueError")
        raw += 1
# 反过来：全等值样本是合法分布（「所有人耗时都是 5 分钟」），必须画得出来
for label, vals in (("全等值", [5.0] * 40), ("单点", [5.0]), ("全零", [0.0] * 12)):
    try:
        step_histogram(vals, title="退化", subtitle="单箱", source="来源")
    except Exception as e:
        bad(f"D1 {label} 样本画不出来：{type(e).__name__}: {e}")
        raw += 1
if not raw:
    ok(f"{len(EMPTY)} 处空输入全部友好拒绝，D1 三种退化样本仍能出图")

# 4.3 · 标签留位 ───────────────────────────────────────────────
# 抽稀留位必须按实测宽度。中西混排下「till」字符最多而「环比增速」最宽，
# 按字符数留位欠 21pt，标签当场叠在一起。这一组同时验证两件事：
# 现在不叠，以及退回旧写法会被校验器第 10 条抓住（否则测试没有牙齿）。
group("标签留位")
_LAB = ["Q1", "Q2", "Q3", "Q4", "till", "环比增速", "同比增速",
        "Q1", "Q2", "till", "环比增速", "Q4"]
_SER = [("甲", [i + 3 for i in range(12)]), ("乙", [14 - i for i in range(12)])]
_kw = dict(title="中西混排刻度", subtitle="副题", source="来源", column="single")


def _overlaps(svg):
    tmp = os.path.join("out", "_labelfit.svg")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(svg)
    hits = [h for h in check(tmp) if "压字" in h]
    os.remove(tmp)
    return hits


now = _overlaps(line_family(_SER, _LAB, **_kw))
_orig_widest = _svg.widest
_svg.widest = lambda ss, z: _svg.text_width(max(ss, key=len), z)   # 退回字符数估宽
try:
    regressed = _overlaps(line_family(_SER, _LAB, **_kw))
finally:
    _svg.widest = _orig_widest
if now:
    bad(f"实测留位下仍有压字：{now}")
elif not regressed:
    bad("退回字符数估宽也没被抓住——校验器第 10 条失效了，这组测试没有牙齿")
else:
    ok(f"实测留位无压字；退回字符数估宽被抓到 {len(regressed)} 条")

# 4.4 · 色板穿透 ───────────────────────────────────────────────
# _svg 原语的颜色默认参数若写进函数签名，会在 def 时求值一次并永久冻结，
# 切了色板也不会变——彩色图里于是混进 mono 的灰。灰度等价测试看不见它：
# mono 灰在彩色图里 L* 完全正确，错的只是色相。
group("色板穿透")
import palettes as _pal
stale = []
for _name in _pal.PRESETS:
    if _name == "mono":
        continue
    with T.use(_name):
        ramp = {c.upper() for c in T.GRAY}
        emitted = {"text": _svg.text(0, 0, "甲"), "rect": _svg.rect(0, 0, 10, 10),
                   "line": _svg.line(0, 0, 10, 10), "path": _svg.path("M0 0"),
                   "circle": _svg.circle(0, 0, 2)}
        for prim, out in emitted.items():
            for hexv in re.findall(r'(?:fill|stroke)="(#[0-9A-Fa-f]{6})"', out):
                if hexv.upper() != "#FFFFFF" and hexv.upper() not in ramp:
                    stale.append(f"{_name}/{prim} 默认参数漏出 {hexv}（不在该色板阶梯内）")
for m in stale:
    bad(m)
if not stale:
    ok(f"{len(_pal.PRESETS) - 1} 套色板 × 5 个原语，默认参数全部跟着色板走")

# 5 · 确定性 ───────────────────────────────────────────────────
group("确定性")
before = {n: open(os.path.join("out", n), "rb").read() for n in svgs}
for script in ("demo.py", "demo_palettes.py"):
    subprocess.run([sys.executable, script], capture_output=True)
drift = [n for n in svgs if open(os.path.join("out", n), "rb").read() != before[n]]
if drift:
    bad(f"两次渲染结果不同：{', '.join(drift)}——演示数据里有随机数")
else:
    ok(f"{len(svgs)} 份产物两次渲染字节一致")

# 5.5 · 导出 ──────────────────────────────────────────────────
# render() 在缺 rsvg-convert 时会静默降级到只出 SVG。CI 上必须
# 装了才算数——否则「能导出 PDF」这条卖点从来没被验证过。
group("导出")
import shutil
if not shutil.which("rsvg-convert"):
    warn("未找到 rsvg-convert，PDF/PNG 导出路径未经验证"
         "（brew install librsvg / apt install librsvg2-bin）")
else:
    thin = []
    for name in svgs:
        stem = name[:-4]
        for ext, floor in (("pdf", 2000), ("png", 2000)):
            path = os.path.join("out", f"{stem}.{ext}")
            if not os.path.exists(path):
                bad(f"{stem}.{ext} 没有产出")
            elif os.path.getsize(path) < floor:
                thin.append(f"{stem}.{ext}({os.path.getsize(path)}B)")
    if thin:
        bad(f"导出文件过小，可能是空白页：{', '.join(thin)}")
    else:
        ok(f"{len(svgs)} 张的 PDF 与 PNG 均已产出")

# 6 · 目录闭环 ─────────────────────────────────────────────────
group("目录闭环")
cat = open("catalog.md", encoding="utf-8").read()
ids = re.findall(r"^\|\s*([RSCDM]\d+)\s*\|.*\|\s*`[^`]+`\s*\|\s*$", cat, re.M)
missing = [i for i in ids if not any(n.startswith(i.lower() + "-") for n in svgs)]
if missing:
    bad(f"catalog 有实现但 demo 没渲染：{', '.join(missing)}")
else:
    ok(f"catalog {len(ids)} 个编号都有渲染产物")

# 7 · 灰度等价 ─────────────────────────────────────────────────
# 彩色档的全部承诺就这一条：色相可以换，明度不能换。守住它，
# 彩色图被黑白影印之后就还是原来那张图；守不住，出版环节会毁掉它。
group("灰度等价")
import palettes
from charts._color import lstar as _ls

HEXPAT = re.compile(r'(?:fill|stroke|data-on)="(#[0-9A-Fa-f]{6})"')


def _profile(path):
    return [_ls(c) for c in HEXPAT.findall(open(path, encoding="utf-8").read())]


worst_all = 0.0
for chart in ("rank", "heat"):
    base_p = os.path.join("out", f"pal-mono-{chart}.svg")
    if not os.path.exists(base_p):
        bad(f"缺少 mono 基准 {base_p}")
        continue
    base = _profile(base_p)
    for pal in palettes.PRESETS:
        if pal == "mono":
            continue
        got = _profile(os.path.join("out", f"pal-{pal}-{chart}.svg"))
        if len(got) != len(base):
            bad(f"{pal}/{chart} 用色处数 {len(got)} ≠ mono 的 {len(base)}")
            continue
        w = max(abs(a - b) for a, b in zip(base, got))
        worst_all = max(worst_all, w)
        if w > 1.0:
            bad(f"{pal}/{chart} 最大明度偏差 {w:.1f} L* > 1.0——影印成灰度后和 mono 版对不上")
if worst_all <= 1.0:
    ok(f"3 套色板 × 2 张，最大明度偏差 {worst_all:.1f} L*")

# ──────────────────────────────────────────────────────────────
print()
if fails:
    print(f"✗ {len(fails)} 项失败")
    sys.exit(1)
print("✓ 全部通过")
