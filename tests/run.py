# -*- coding: utf-8 -*-
"""测试入口。CI 和本地都跑这一个：python3 tests/run.py

六组检查：
  1 渲染      全部图型能画出来
  2 校验      产物 / token / 目录 / README 全部合规
  3 反例      校验器仍然抓得住违规，条数不少于预期
  4 越界      每张有上限的图型都会拒绝超限数据
  4.01 闸门   validate.py 的退出码本身要对（不给参数必须失败）
  4.02 盲区   定点突变，每处都要被对应的那条规则点名
  4.05 界内   恰好取到声明的上限那一档，必须画得出来且合规
  4.06 数值   数值永不排成科学计数法（:,g 在 |v| ≥ 1e6 时会）
  4.1 负值    长度编码的图会拒绝负值，而不是画出零长条
  4.2 退化    空数据一律友好拒绝；全等值样本仍要画得出来
  4.3 留位    标签抽稀按实测宽度，退回字符数估宽必须被抓住
  4.4 色板    切色板后原语默认参数必须跟着走，不许漏出 mono 灰
  4.5 版心    13 张 × 5 档栏宽全部渲染并合规；图形区高度随栏宽增长
  4.7 字宽    东亚歧义宽度字符在中文串里按整字身算（「·」实测差 3.6 倍）
  5 确定性    清空 out/ 后跑两次，字节与产物清单都相同
  5.5 导出    PDF / PNG 真的产出、不是空白页；PNG 带 300dpi 分辨率块
  6 目录闭环  catalog 里每个编号都有渲染产物
  7 灰度等价  13 张 × 3 套色板，逐处用色的明度必须与 mono 版一致
"""
import io, os, re, shutil, struct, subprocess, sys, contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import tests.badcase as badcase
import tokens as T
from charts import _svg
from scripts.validate import check, check_tokens, check_catalog, check_docs

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
# 先清空 out/。不清的话，上一次跑剩的文件会被当成本次产物——实测把一份
# zz-stale.svg（连同 pdf/png）放进去，全套照样 exit=0，而且一本正经地报
# 「22 份产物两次渲染字节一致」：那一份这两次都没有被渲染过。
# 一条能被陈旧文件满足的确定性承诺，就不再是承诺。
if os.path.isdir("out"):
    shutil.rmtree("out")
os.makedirs("out", exist_ok=True)

# examples/ 一并渲染。它们不进这条流水线就会烂——真实数据的例子最容易
# 因为一次改签名、一次改 token 而悄悄失效，而它们恰恰是外人第一眼看的东西。
# 进来之后，下游每一组（校验 / 确定性 / 导出）自动覆盖到它们。
RENDER = ("demo.py", "demo_palettes.py",
          os.path.join("examples", "ex1_population.py"),
          os.path.join("examples", "ex2_life_expectancy.py"),
          os.path.join("examples", "ex3_urbanization.py"))

group("渲染")
for script in RENDER:
    r = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if r.returncode:
        bad(f"{script} 失败：{r.stderr.strip()[:200]}")
    else:
        ok(r.stdout.strip().splitlines()[-1])

svgs = sorted(f for f in os.listdir("out") if f.endswith(".svg")
              and not f.startswith("_"))

# 2 · 校验 ─────────────────────────────────────────────────────
group("校验")
for f in (check_tokens(), check_catalog(), check_docs()):
    for m in f:
        bad(m)
if not (check_tokens() or check_catalog() or check_docs()):
    ok("tokens.py / catalog.md / README.md 自检通过")
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
from charts.rank_bars import rank_bars
from charts.diverging_bars import diverging_bars
from charts.day_series import day_series
from datetime import date, timedelta

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
    # 以下四道 catalog 早就声明了，但一直没有代码兜住
    ("R1 窄栏类目超限", rank_bars, ([(f"类{i}", 10) for i in range(9)],)),
    ("R2 类目超限", diverging_bars, ([(f"类{i}", 10) for i in range(11)],)),
    ("S1 天数超限", day_series, ([(date(2026, 1, 1) + timedelta(days=i), 10)
                                  for i in range(151)],)),
    ("D2 点数超限", beeswarm, ([("甲", [1] * 181)],)),
]
# 不能只看「抛没抛 ValueError」。两个理由：
#   一是替身——拦下它的可能是另一道守卫，那么被测的这道其实已经失效了，
#     而测试照样绿。所以断言报错里点了名：每道上限的话都以「<编号> …最多」开头。
#   二是崩溃——`except ValueError` 不接别的异常。实测把 S2 的 MAX_SERIES
#     守卫改成 `if False:`，8 条线会走到 widths[6] 抛 IndexError，
#     **整个测试进程当场被冲垮，后面每一组一条都没跑**。一道守卫坏掉
#     不该把整套测试的结论一起带走，所以这里接住所有异常，分开报。
def guard_check(label, fn, args, kw, want):
    code = label.split()[0]
    try:
        fn(*args, title="越界", **kw)
    except ValueError as e:
        msg = str(e)
        if not msg.startswith(code) or want not in msg:
            return (f"{label} 是被拦下了，但报错不是这道守卫说的话"
                    f"（期望以「{code}」开头且含「{want}」，实得「{msg[:44]}」）"
                    f"——被别的守卫顶了包，这道其实已经失效")
        return None
    except Exception as e:
        return (f"{label} 抛的是 {type(e).__name__}: {str(e)[:40]}，不是给用户的"
                f"改图建议。裸异常还会把整套测试冲垮，后面每一组都不会跑。")
    return f"{label} 未被拦下"


leaked = 0
for label, fn, args in GUARDS:
    m = guard_check(label, fn, args, {}, "最多")
    if m:
        bad(m)
        leaked += 1
if not leaked:
    ok(f"{len(GUARDS)} 道上限全部生效，且都是这道守卫自己报的错")

# R3 的上限不是类目数，是「这么多点摆不摆得下」，所以上面那张表测不到它。
# 两条路径分开测：
#   自动定档必须无上限地跟着量级走。上一版是查表（1,2,5,…,10000），需求
#   一旦超过最大档就一次都不 break，per_dot 停在初值 1——160 万的输入
#   照单全收，画出 160 万个 <circle>，几十 MB、几十米高的 SVG。
#   不抛异常、不崩溃，校验器也判不出来（它不看几何），只是没法用。
from charts.dot_cascade import dot_cascade as _dc, per_dot_for, dots_for

# 判在纯函数上，不判在产物上：这条逻辑一旦退回查表，per_dot 会回到 1，
# 而「渲染出来再数 <circle>」意味着测试真的要去画那 30 亿个点——
# 那是把自己挂死，不是变红。回归必须在一次函数调用里当场失败。
blown = []
for _vmax in (1_500_000, 1_600_000, 50_000_000, 3_000_000_000):
    _pd = per_dot_for(_vmax, 150)
    _n = dots_for(_vmax, _pd)
    if _n > 150:
        blown.append(f"vmax={_vmax:,} 定出 per_dot={_pd:,}，仍要画 {_n:,} 个点"
                     f"（一张图摆得下 150 个）——每点当量没跟着量级走")
for m in blown:
    bad(m)
# 界内的量级仍要照常出图，别为了防大数把小数据也推上高档位
_note = _dc([("甲", 5_000), ("乙", 1_200)], title="量级",
            subtitle="口径", source="来源")
if _note.count("<circle") > 150:
    bad("R3 在 5,000 这种寻常量级上画超了 150 个点")
#   显式传进来的 per_dot 装不下时，同样不能闷头画。
try:
    _dc([("甲", 1_600_000)], per_dot=10, title="越界")
    bad("R3 显式 per_dot 装不下时未被拦下——会画出十六万个点")
    blown.append(1)
except ValueError:
    pass
if not blown:
    ok("R3 每点当量随量级无上限地走，显式传的装不下时当场拒绝")

# 4.005 · 选型记录 ────────────────────────────────────────────
# SKILL.md 第一节第 3 条：「在 catalog.md 里至少比较 3 个候选，写下淘汰理由。
# 只记录『用了哪张』不算数——选择过程本身是交付物的一部分。」
#
# 这是全份文档里分量最重、却最没法执行的一条：它要求的是一段思考过程，
# 而思考过程写没写，此前既没有产物也没有检查。examples/ 是它第一次有实物，
# 那就顺手把它判起来——判不了「理由好不好」，但判得了「有没有、够不够三个」。
# 一个采用、至少两个淘汰，且淘汰理由不能是空话（得给出替代图型或数据形状）。
group("选型记录")
_ex = sorted(f for f in os.listdir("examples")
             if f.startswith("ex") and f.endswith(".py"))
_thin = 0
if not _ex:
    bad("examples/ 下一个例子都没有——路线图上这一项还没兑现")
    _thin += 1
for _f in _ex:
    _src = open(os.path.join("examples", _f), encoding="utf-8").read()
    _doc = _src.split('"""')[1] if '"""' in _src else ""
    _taken = _doc.count("← 采用")
    _cut = _doc.count("—— 淘汰")
    if "选型" not in _doc:
        bad(f"examples/{_f} 的文档字符串里没有选型记录")
        _thin += 1
    elif _taken != 1 or _taken + _cut < 3:
        bad(f"examples/{_f} 的选型记录不完整：{_taken} 个「← 采用」、"
            f"{_cut} 个「—— 淘汰」，要求恰好 1 个采用且候选合计 ≥3")
        _thin += 1
    elif not re.search(r"数据形状|catalog|失效条件", _doc):
        bad(f"examples/{_f} 的淘汰理由没有落到数据形状或 catalog 的失效条件上"
            f"——那样的理由是空话，谁都可以事后编一个")
        _thin += 1
if not _thin:
    ok(f"{len(_ex)} 个例子都写了选型过程：1 个采用 + ≥2 个带理由的淘汰")

# 4.01 · 交付闸门 ─────────────────────────────────────────────
# SKILL.md 第零节第 7 条把 `python3 scripts/validate.py out/*.svg` 的退出码
# 当作交付闸门。那条命令在两种情况下会**空过**，而两种都正好是最该拦住的：
#   · 一张图都没出：glob 匹配不到文件，shell 传进来零个参数，
#     校验器照旧打印「0 个文件，0 项不合格」并退出 0；
#   · 某一份读不了：裸 traceback 中断整个循环，后面几十份一份都没查，
#     而退出码非零，看起来倒像是「它拦下了什么」。
# 闸门自己没被测过，等于整条硬约束建在沙上。
group("交付闸门")
_V = [sys.executable, os.path.join("scripts", "validate.py")]
GATE = [
    ("不给参数（out/ 是空的就是这样）", [], 2),
    ("--help", ["--help"], 0),
    ("文件不存在", [os.path.join("out", "nope.svg")], 1),
    ("正常产物", [os.path.join("out", n) for n in svgs], 0),
]
_gate_bad = 0
for _label, _args, _want in GATE:
    _r = subprocess.run(_V + _args, capture_output=True, text=True)
    if _r.returncode != _want:
        bad(f"交付闸门「{_label}」退出码 {_r.returncode}，应为 {_want}")
        _gate_bad += 1
# 一份坏文件不能把后面的检查一起带走
_r = subprocess.run(_V + [os.path.join("out", "nope.svg"),
                          os.path.join("out", svgs[0])], capture_output=True, text=True)
if svgs[0] not in _r.stdout:
    bad("一份文件读不了就中断了整个循环——后面的产物一份都没被检查")
    _gate_bad += 1
if not _gate_bad:
    ok(f"{len(GATE)} 种调用方式退出码都对，坏文件不会带走后面的检查")

# 4.02 · 校验器盲区 ───────────────────────────────────────────
# 定点突变：拿一份真实合规的产物，改坏一处，断言**对的那条规则**开口。
#
# 反例组（badcase）只数命中条数，数够就算过——一条规则被删掉，另一条
# 恰好多吐一条，总数不变，它看不出来。这一组按关键词点名，规则和用例
# 一一对应，删哪条就红哪条。
#
# 这些突变全部是「肉眼看不出、diff 看得见」的那种：px 换 pt 数字一模一样，
# viewBox 翻倍后图还是那张图，只是落纸尺寸和每一条 pt 判定一起错位。
group("校验器盲区")
_good = open(os.path.join("out", "r1-rank-bars.svg"), encoding="utf-8").read()
_dots = open(os.path.join("out", "r3-dot-cascade.svg"), encoding="utf-8").read()

MUTATIONS = [
    ("宽度单位换成 px", _good, lambda s: s.replace('width="240.945pt"', 'width="240.945px"'),
     "不是 pt"),
    ("高度单位换成 px", _good, lambda s: s.replace('height="198.0pt"', 'height="198.0px"'),
     "不是 pt"),
    ("viewBox 放大一倍", _good, lambda s: s.replace('viewBox="0 0 240.945 198.0"',
                                                    'viewBox="0 0 481.89 396.0"'),
     "对不上"),
    ("条跑到纸外", _good, lambda s: s.replace('<rect x="6" y="50.0" width="203.625"',
                                              '<rect x="6" y="50.0" width="403.625"'),
     "越出版心"),
    ("条被吞成负坐标", _good, lambda s: s.replace('<rect x="6" y="50.0"',
                                                  '<rect x="-40" y="50.0"'),
     "越出版心"),
    ("图高长到纸外", _good, lambda s: s.replace('<line x1="6" y1="37.5" x2="6" y2="174.5"',
                                                '<line x1="6" y1="37.5" x2="6" y2="974.5"'),
     "越出版心"),
    ("点缩到地板以下", _dots, lambda s: s.replace('r="1.6"', 'r="0.2"'),
     "点半径"),
    # 443mm——比 A4 还高 50%。校验器此前只读 width、从不读 height，
    # 这张图零告警通过；宽度判得再严，高度不判就是只判了一半。
    ("图比纸还高", _good, lambda s: s.replace(
        'height="198.0pt"\n     viewBox="0 0 240.945 198.0"',
        'height="1255.7pt"\n     viewBox="0 0 240.945 1255.7"'),
     "图高"),
    ("混进线性渐变", _good, lambda s: s.replace("<rect width=\"100%\"",
                                                "<linearGradient id=\"g\"/><rect width=\"100%\""),
     "linearGradient"),
    ("填充指向渐变", _good, lambda s: s.replace('fill="#1F1F1F"/>', 'fill="url(#g)"/>', 1),
     "url("),
    ("用 alpha 表达密度", _good, lambda s: s.replace('<rect x="6" y="50.0"',
                                                     '<rect fill-opacity="0.08" x="6" y="50.0"'),
     "落不上纸"),
    # stroke 通道：S1/S2/D1 的数据全编码在描边上，只收 fill 等于没判过它们
    ("描边灰度过近", _good, lambda s: s.replace('stroke="#969696"', 'stroke="#8A8A8A"'),
     "灰度过近"),
    ("字号带单位（旧版会裸崩）", _good, lambda s: s.replace('font-size="10.5"', 'font-size="4pt"'),
     "下限"),
]
_toothless = 0
for _label, _base, _mut, _want in MUTATIONS:
    _tmp = os.path.join("out", "_mut.svg")
    _broken = _mut(_base)
    if _broken == _base:
        bad(f"突变锚点漂了，改不出违规：{_label}")
        _toothless += 1
        continue
    with open(_tmp, "w", encoding="utf-8") as fh:
        fh.write(_broken)
    try:
        _hits = check(_tmp)
    except Exception as e:                # 校验器崩掉 = 这份产物根本没被检查
        bad(f"「{_label}」让校验器抛了 {type(e).__name__}: {e}")
        _toothless += 1
        os.remove(_tmp)
        continue
    if not any(_want in m for m in _hits):
        bad(f"「{_label}」没被对应规则抓住（期望命中含「{_want}」，实得 {_hits or '零条'}）")
        _toothless += 1
    os.remove(_tmp)
if not _toothless:
    ok(f"{len(MUTATIONS)} 处定点突变全部被对应的规则当场点名")

# 4.05 · 界内正例 ─────────────────────────────────────────────
# 只测「超限会被拒」是不够的。上限声明得再响，**恰好取到上限那一档**
# 画不出来，文档就是在替一个不存在的能力背书。S2 就是这么活下来的：
# catalog 白纸黑字写着「≤6（代码强制）」，而线宽表末两档撞在一起，
# 第 6 条线撞上「(灰阶, 线宽) 必须两两不同」的守卫——越界组只喂 8 条，
# 看到 ValueError 就算过，永远碰不到第 6 条这个真正的边界。
#
# 上限直接从各图型的常数取，不在这里抄数字：谁把 MAX_ 调小，这一组
# 跟着调小，声明和实现不会各走各的。
group("界内正例")
from charts.hundred_grid import MAX_CATS as C1_MAX
from charts.beeswarm import MAX_GROUPS as D2_MAX_G, MAX_POINTS as D2_MAX_P
from charts.matrix_heat import MAX_CELLS as M1_MAX
from charts.tick_box import MAX_GROUPS as D3_MAX
from charts.line_family import MAX_SERIES as S2_MAX
from charts.small_multiples import MAX_PANELS as S3_MAX
from charts.stacked_bands import MAX_LAYERS as C2_MAX
from charts.rank_bars import MAX_CATS_NARROW as R1_MAX_N, MAX_CATS_WIDE as R1_MAX_W
from charts.diverging_bars import MAX_CATS as R2_MAX
from charts.day_series import MAX_DAYS as S1_MAX

_xs = lambda n: [f"{i+1}月" for i in range(n)]
_side = int(M1_MAX ** 0.5)

AT_CAP = [
    (f"R1 窄栏 {R1_MAX_N} 项", rank_bars,
     ([(f"类{i}", 100 - i * 7) for i in range(R1_MAX_N)],), {}),
    (f"R1 宽栏 {R1_MAX_W} 项", rank_bars,
     ([(f"类{i}", 100 - i * 7) for i in range(R1_MAX_W)],), {"column": "double"}),
    (f"R2 {R2_MAX} 项", diverging_bars,
     ([(f"类{i}", 20 - i * 5) for i in range(R2_MAX)],), {}),
    (f"C1 {C1_MAX} 类", hundred_grid,
     ([("甲", 30), ("乙", 25), ("丙", 20), ("丁", 13), ("戊", 7), ("己", 5)][:C1_MAX],), {}),
    (f"C2 {C2_MAX} 层", stacked_bands,
     ([(f"层{i}", [10 + i, 12 + i, 11 + i]) for i in range(C2_MAX)], _xs(3)), {}),
    (f"S1 {S1_MAX} 天", day_series,
     ([(date(2026, 1, 1) + timedelta(days=i), 100 + (i % 17)) for i in range(S1_MAX)],), {}),
    (f"S2 {S2_MAX} 条", line_family,
     ([(f"序列{i}", [10 + i * 3 + j for j in range(12)]) for i in range(S2_MAX)], _xs(12)), {}),
    (f"S3 {S3_MAX} 格", small_multiples,
     ([(f"格{i}", [5 + i, 8 + i, 6 + i]) for i in range(S3_MAX)], _xs(3)), {}),
    (f"D2 {D2_MAX_G} 组", beeswarm,
     ([(f"组{i}", [10 + (j * 7 + i * 3) % 40 for j in range(20)])
       for i in range(D2_MAX_G)],), {}),
    (f"D2 {D2_MAX_P} 点", beeswarm,
     ([("甲", [10 + (j * 13) % 50 for j in range(D2_MAX_P)])],), {}),
    (f"D3 {D3_MAX} 组", tick_box,
     ([(f"组{i}", [5 + i, 9 + i, 12 + i, 15 + i, 21 + i]) for i in range(D3_MAX)],), {}),
    (f"M1 {M1_MAX} 格", matrix_heat,
     ([f"行{i}" for i in range(_side)], [f"列{j}" for j in range(_side)],
      [[(i * _side + j) % 40 for j in range(_side)] for i in range(_side)]), {}),
]
unreachable = 0
for label, fn, args, kw in AT_CAP:
    tmp = os.path.join("out", "_atcap.svg")
    try:
        svg = fn(*args, title="界内正例", subtitle="口径 · 单位", source="来源", **kw)
    except ValueError as e:
        bad(f"{label}：声明的上限画不出来——{e}")
        unreachable += 1
        continue
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(svg)
    for m in check(tmp):
        bad(f"{label}：恰好取到上限时不合规——{m}")
        unreachable += 1
    os.remove(tmp)
if not unreachable:
    ok(f"{len(AT_CAP)} 处声明的上限，恰好取到那一档都画得出来且合规")

# 4.06 · 数值格式 ─────────────────────────────────────────────
# `f"{v:,g}"` 在 |v| ≥ 1e6 时切到科学计数法：营收 1234567 印成
# 「1.23457e+06」。校验器第 12 条判产物，这一组判函数本身——两头都堵上，
# 因为这类错的特征就是**一路合法**：字号、字色、宽度、对比度全部合规。
group("数值格式")
from charts._data import num as _num

SCI = re.compile(r"\d[eE][+-]\d")
_vals = [0, 1, 12.5, 189.5, 999.5, 3820, 999_999, 1_000_000, 1_234_567,
         89_000_000, 3e9, -1_234_567, 0.045, 0.0001, 1e-9]
_sci = [f"num({v!r}) = {_num(v)}" for v in _vals if SCI.search(_num(v))]
for m in _sci:
    bad(f"数值排成了科学计数法：{m}")
# 对照：这些值里必须真有会让 :,g 翻车的，否则这组测试没有牙齿。
_would = [v for v in _vals if SCI.search(f"{v:,g}")]
if not _would:
    bad("对照用例里没有一个会让 :,g 切到科学计数法——这组测试没有牙齿")
elif not _sci:
    ok(f"{len(_vals)} 个量级 num() 全部不走科学计数法"
       f"（其中 {len(_would)} 个 :,g 会翻车）")
# 显式 decimals 仍要补零对齐，不许被自动档的去尾逻辑吃掉
if _num(95.0, decimals=1) != "95.0" or _num(3, decimals=2) != "3.00":
    bad("num() 传了 decimals 还去尾——同一组数的小数位对不齐了")

# 4.1 · 负值防护 ───────────────────────────────────────────────
# 长度 / 个数 / 面积 ∝ 数值的图收到负值时，几何没有对应的画法：
# 条被 max(w,0) 吞成零长、跟在条端的数值跑到纸外、百格方阵分出 165 格。
# 画一张撒谎的图比报错糟得多，所以这些必须当场拒绝。
group("负值防护")
from charts.dot_cascade import dot_cascade
from charts.scatter_fit import scatter_fit
from charts.step_histogram import step_histogram

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
    # 同样要点名。负值守卫和类目上限守卫都抛 ValueError，只看类型的话，
    # 一张图的负值守卫失效、恰好被别的守卫拦下，测试是看不出来的。
    # 关键词取「负值」而不是 require_nonneg 那句「不接受负值」：S2 有它
    # 自己更贴切的说法（y_from_zero=True 会把标度域钉在 0）。编号前缀已经
    # 保证了是这张图自己的守卫，措辞不必强求统一。
    m = guard_check(label, fn, args, {}, "负值")
    if m:
        bad(m.replace("未被拦下", "未被拦下——画出了一张长度不 ∝ 数值的图"))
        leaked += 1
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

# 4.5 · 版心覆盖 ───────────────────────────────────────────────
# demo 只跑 single 和 double，COLUMN 却有五档——onehalf / a4body / slide
# 长期处于「从没渲染过」的状态。第一次把 13 × 5 跑全，就抓到了 D1 最后一个
# 箱边标签出血（demo 的标签是整数「70」，窄得刚好塞得进右边距，一直没露）。
group("版心覆盖")
import tests.fixtures as fx

miss = 0
for code, draw in fx.ALL:
    for col in T.COLUMN:
        tmp = os.path.join("out", "_cov.svg")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(draw(col))
        except Exception as e:
            bad(f"{code}/{col} 画不出来：{type(e).__name__}: {e}")
            miss += 1
            continue
        for m in check(tmp):
            bad(f"{code}/{col}: {m}")
            miss += 1
        os.remove(tmp)
if not miss:
    ok(f"{len(fx.ALL)} 张 × {len(T.COLUMN)} 档 = {len(fx.ALL) * len(T.COLUMN)} 种组合全部合规")

# 图形区高度必须随栏宽长。写成硬编码常数时，slide 栏（254mm）拿到的高度
# 和 single 栏（85mm）一模一样，整图被压成 0.25 的扁带。
thin = []
for code, draw in fx.ALL:
    if code not in fx.RESPONSIVE:
        continue
    hs = {}
    for col in ("single", "slide"):
        m = re.search(r'height="([\d.]+)pt"', draw(col))
        hs[col] = float(m.group(1))
    if hs["slide"] < hs["single"] * 1.3:
        thin.append(f"{code} 在 slide 栏只有 {hs['slide']:.0f}pt 高，"
                    f"single 栏是 {hs['single']:.0f}pt——图形区高度没跟着栏宽长")
for m in thin:
    bad(m)
if not thin:
    ok(f"{len(fx.RESPONSIVE)} 张按宽度推导高度的图，slide 档均比 single 档高 ≥30%")

# 4.6 · 目录声明一致性 ─────────────────────────────────────────
# 「类目上限」列里写了数字就必须标「代码强制」并真的拦住。这条规则本身
# 也要有反例——否则它跟着 catalog 一起漂掉都没人知道。
group("文档声明一致性")
_cat = open("catalog.md", encoding="utf-8").read()
_rme = open("README.md", encoding="utf-8").read()
DOC_CASES = [
    ("catalog 抹掉一处「代码强制」", lambda: check_catalog(_cat.replace("≤10（代码强制）", "≤10")),
     "≤10（代码强制）" in _cat),
    ("catalog 分区标回「待建」", lambda: check_catalog(
        _cat.replace("## S 系 · 时间序列", "## S 系 · 时间序列（待建）")),
     "## S 系 · 时间序列" in _cat),
    ("README 行数声明写错", lambda: check_docs(
        re.sub(r"决策规则，\d+ 行", "决策规则，78 行", _rme)),
     bool(re.search(r"决策规则，\d+ 行", _rme))),
    ("README 图型表少一行", lambda: check_docs(
        _rme.replace("| M2 | 散点带回归 | 两个连续变量是否共变 | 85mm 单栏 |\n", "")),
     "| M2 | 散点带回归 |" in _rme),
    ("CI 徽标指向不存在的 workflow", lambda: check_docs(
        _rme.replace("ci.yml/badge.svg", "build.yml/badge.svg")),
     "ci.yml/badge.svg" in _rme),
]
toothless = 0
for label, run, anchored in DOC_CASES:
    if not anchored:
        bad(f"反例锚点漂了，改不出违规：{label}")
        toothless += 1
    elif not run():
        bad(f"「{label}」没被抓住——对应规则失效了")
        toothless += 1
if not toothless:
    ok(f"{len(DOC_CASES)} 处文档漂移全部会被当场抓住")

# 4.7 · 字宽估计 ───────────────────────────────────────────────
# 「·」这类东亚歧义宽度（UAX-11 Ambiguous）字符，在拉丁字体里 0.278em、
# 在 CJK 字体里 1.000em——实测自 Helvetica Neue 与 Hiragino Sans GB 的
# hmtx 表。SVG 逐字符 fallback，所以同一份文件在装了 Inter 的机器和只装
# Noto CJK 的机器（CI 的 runner 就是）上宽度不同。印刷控制不了 RIP 的字体，
# 只能按最宽的算。这一档估窄了，中文副题一行两三个间隔号就少算十几 pt。
group("字宽估计")
_narrow_stand_in = "l"          # 一个确定属于窄档的 ASCII 字符
cjk_with = _svg.text_width("甲 · 乙 · 丙", 9.0)
cjk_without = _svg.text_width(f"甲 {_narrow_stand_in} 乙 {_narrow_stand_in} 丙", 9.0)
lat_with = _svg.text_width("a · b", 9.0)
wrong = []
if cjk_with - cjk_without < 9.0 * 2 * (1.0 - 0.30) - 0.01:
    wrong.append(f"中文串里的「·」没有按整字身算：两个间隔号只多出 "
                 f"{cjk_with - cjk_without:.1f}pt，应为 {9.0 * 2 * 0.7:.1f}pt 以上")
if lat_with >= _svg.text_width("a m b", 9.0):
    wrong.append("纯拉丁串里的「·」被当成了全角——那一档只在中文上下文成立")
if "·" in _svg._NARROW:
    wrong.append("「·」还留在 _NARROW 里，会抢在歧义宽度判定之前被当成窄字符")
for m in wrong:
    bad(m)
if not wrong:
    ok("歧义宽度按上下文取宽：中文串里 1.0em，纯拉丁串里按拉丁算")

# 5 · 确定性 ───────────────────────────────────────────────────
group("确定性")
# 清空之后再渲染一次：既比字节，也比产物清单。只覆盖不清空的话，
# 某张图从此不再产出（比如被误删了调用）也发现不了——旧文件还躺在那儿。
before = {n: open(os.path.join("out", n), "rb").read() for n in svgs}
shutil.rmtree("out")
os.makedirs("out", exist_ok=True)
for script in RENDER:
    subprocess.run([sys.executable, script], capture_output=True)
again = sorted(f for f in os.listdir("out") if f.endswith(".svg") and not f.startswith("_"))
if again != svgs:
    bad(f"两次渲染的产物清单不同：多出 {sorted(set(again) - set(svgs))}，"
        f"少了 {sorted(set(svgs) - set(again))}")
drift = [n for n in svgs if n in again
         and open(os.path.join("out", n), "rb").read() != before[n]]
if drift:
    bad(f"两次渲染结果不同：{', '.join(drift)}——演示数据里有随机数")
else:
    ok(f"{len(svgs)} 份产物两次渲染字节一致")

# 5.5 · 导出 ──────────────────────────────────────────────────
# render() 在缺 rsvg-convert 时会静默降级到只出 SVG。CI 上必须
# 装了才算数——否则「能导出 PDF」这条卖点从来没被验证过。
group("导出")
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

    # 像素数对，不等于尺寸对。rsvg-convert 的 --dpi 只决定栅格化算出多少
    # 像素，不往文件里写分辨率——缺了 pHYs 块，Word / InDesign / LaTeX
    # 一律按 72dpi 解释，85mm 的图置入时变成 354mm。README 承诺的
    # 「300dpi PNG，直接置入 Word」，全落在这 9 个字节上。
    def png_dpi(raw):
        """读 pHYs，返回 (dpi_x, dpi_y)；没有这块或单位不是米则返回 None。"""
        i = 8
        while i < len(raw):
            ln = struct.unpack(">I", raw[i:i + 4])[0]
            typ = raw[i + 4:i + 8]
            if typ == b"pHYs":
                x, y, unit = struct.unpack(">IIB", raw[i + 8:i + 17])
                return (x * 0.0254, y * 0.0254) if unit == 1 else None
            if typ == b"IDAT":       # pHYs 若在 IDAT 之后，解码器不认，等同于没有
                return None
            i += 12 + ln
        return None

    def dpi_fails(raw, pt_w):
        """这张 PNG 在「300dpi 1:1 落纸」上的问题清单。空列表表示合格。"""
        out = []
        d = png_dpi(raw)
        if d is None:
            out.append("不带 pHYs 分辨率块，置入时会被按 72dpi 解释（放大 4.17 倍）")
        elif abs(d[0] - 300) > 0.5 or abs(d[1] - 300) > 0.5:
            out.append(f"pHYs 写的是 {d[0]:.1f}×{d[1]:.1f}dpi，不是 300")
        px_w = struct.unpack(">I", raw[16:20])[0]
        want = round(pt_w / 72 * 300)
        if abs(px_w - want) > 1:
            out.append(f"宽 {px_w}px，而版心 {pt_w:.1f}pt @300dpi 应为 {want}px")
        return out

    dpi_bad, sample = [], None
    for name in svgs:
        stem = name[:-4]
        path = os.path.join("out", f"{stem}.png")
        if not os.path.exists(path):
            continue
        head = open(os.path.join("out", name), encoding="utf-8").read(400)
        pt_w = float(re.search(r'width="([\d.]+)pt"', head).group(1))
        raw = open(path, "rb").read()
        if sample is None:
            sample = (raw, pt_w)
        for m in dpi_fails(raw, pt_w):
            dpi_bad.append(f"{stem}.png {m}")
    for m in dpi_bad[:5]:
        bad(m)
    # 反例：把 pHYs 抠掉，这组检查必须当场抓住。缺了这条，检查跟着
    # render.py 一起漂掉都没人会发现——像素数照样是对的，肉眼没有区别，
    # 只有把图拖进 Word 的那个人会知道。
    if sample and not dpi_bad:
        raw, pt_w = sample
        i, stripped = 8, [raw[:8]]
        while i < len(raw):
            ln = struct.unpack(">I", raw[i:i + 4])[0]
            if raw[i + 4:i + 8] != b"pHYs":
                stripped.append(raw[i:i + 12 + ln])
            i += 12 + ln
        if not dpi_fails(b"".join(stripped), pt_w):
            bad("抠掉 pHYs 也没被抓住——PNG 分辨率检查失效了，这组测试没有牙齿")
        else:
            ok(f"{len(svgs)} 张 PNG 均带 300dpi 分辨率块，像素数与版心宽度对得上")

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


def _profile_text(svg):
    return [_ls(c) for c in HEXPAT.findall(svg)]


# 覆盖全部 13 张，不是只覆盖 demo_palettes 出的那 2 张。
#
# 先说清楚这一步买到了什么：**当前一条也多抓不到。** 实测 R1 + M1 两张
# 已经把七级明度 {12,25,37,49,62,76,88} 全部用到了，其余 11 张没有带来
# 任何新的明度；把 LADDER 改偏 3 L*，第一个报的也是 R1。
# 留着它是为了以后：某张图一旦不再直接取 ramp（混色、加网、按数据插值），
# L* 就可能只在那张图上漂，而 R1/M1 看不见。代价是 39 次渲染，不花时间。
#
# 真正当场解掉的是另一件事：不再依赖 out/pal-*.svg 存在。现场渲染，
# demo_palettes 出没出图都不影响这条最重的承诺被检查。
worst_all, n_pairs = 0.0, 0
for code, draw in fx.ALL:
    base = _profile_text(draw("single"))
    for pal in palettes.PRESETS:
        if pal == "mono":
            continue
        with T.use(pal):
            got = _profile_text(draw("single"))
        if len(got) != len(base):
            bad(f"{pal}/{code} 用色处数 {len(got)} ≠ mono 的 {len(base)}")
            continue
        w = max((abs(a - b) for a, b in zip(base, got)), default=0.0)
        worst_all = max(worst_all, w)
        n_pairs += 1
        if w > 1.0:
            bad(f"{pal}/{code} 最大明度偏差 {w:.1f} L* > 1.0——影印成灰度后和 mono 版对不上")
if worst_all <= 1.0:
    ok(f"{len(fx.ALL)} 张 × {len(palettes.PRESETS) - 1} 套色板 = {n_pairs} 组，"
       f"最大明度偏差 {worst_all:.1f} L*")

# ──────────────────────────────────────────────────────────────
print()
if fails:
    print(f"✗ {len(fails)} 项失败")
    sys.exit(1)
print("✓ 全部通过")
