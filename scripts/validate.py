# -*- coding: utf-8 -*-
"""产物校验：对生成的 SVG 逐项核印刷规范。能机器判的一律不指望模型自觉。

用法：python3 scripts/validate.py out/*.svg
"""
import re, sys, os, xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens as T
from charts import _svg as S

NS = "{http://www.w3.org/2000/svg}"


def _lum(hexcolor):
    """相对亮度（WCAG）。同时也是这张图印成灰度后的明度。"""
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    ch = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        ch.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def lstar(hexcolor):
    """CIE L* 明度。感知均匀——这才是"两个灰印出来分不分得开"的正确度量。
    之前用相对亮度差判定，暗端两级的亮度差天然就小，会误报。"""
    Y = _lum(hexcolor)
    return 116 * (Y ** (1 / 3)) - 16 if Y > 0.008856 else 903.3 * Y


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _f(el, attr, default=0.0):
    """读一个可能带单位的数值属性。

    `float(el.get("font-size"))` 碰上 `font-size="5pt"` 会裸崩，而校验器
    崩掉等于这份产物**根本没被检查**——比报一条错危险得多：退出码非零，
    看起来像「被拦下了」，实际上后面几十条规则一条都没跑。
    """
    v = el.get(attr)
    if v is None:
        return default
    m = re.match(r"\s*(-?[\d.]+)", v)
    return float(m.group(1)) if m else default


def _box(el, tag):
    """图元的包围盒 (x0, y0, x1, y1)；量不出来的返回 None。

    百分比尺寸（纸底那块 `<rect width="100%">`）直接跳过——它按定义
    就是整幅，判它没有意义。
    """
    def n(a):
        v = el.get(a)
        return None if v is None or v.strip().endswith("%") else _f(el, a)

    if tag == "rect":
        x, y, w_, h_ = n("x"), n("y"), n("width"), n("height")
        if None in (x, y, w_, h_):
            return None
        return (x, y, x + w_, y + h_)
    if tag == "circle":
        cx, cy, r = n("cx"), n("cy"), n("r")
        if None in (cx, cy, r):
            return None
        return (cx - r, cy - r, cx + r, cy + r)
    if tag == "line":
        v = [n("x1"), n("y1"), n("x2"), n("y2")]
        if None in v:
            return None
        return (min(v[0], v[2]), min(v[1], v[3]), max(v[0], v[2]), max(v[1], v[3]))
    if tag == "path":
        v = [float(x) for x in re.findall(r"-?\d+\.?\d*", el.get("d", ""))]
        if len(v) < 2:
            return None
        xs, ys = v[0::2], v[1::2]
        return (min(xs), min(ys), max(xs), max(ys))
    return None


def check(path):
    src = open(path, encoding="utf-8").read()
    root = ET.fromstring(src)
    fails = []

    # 色板名写在根元素上。不读它的话，彩色图的每一处用色都会被
    # 拿 mono 灰阶去比，全部误报。
    import palettes
    pname = root.get("data-palette", "mono")
    try:
        ramp = palettes.build(pname) or T.MONO
    except ValueError:
        fails.append(f"根元素声明了不存在的色板 data-palette=\"{pname}\"")
        ramp = T.MONO

    # 1 · 尺寸必须以 pt 为单位、宽度落在版心表里，且 viewBox 与之 1:1。
    #
    #     单位不能剥掉了事。上一版是 `re.sub(r"[a-z]+$", "", ...)`——
    #     width="240.945px" 被剥成同一个数字，判定完全一样，而纸上的尺寸
    #     差了 4.17 倍。这个项目的立身之本就是「SVG 用户单位即 pt，1:1 落纸」，
    #     那这一条就得判在单位上，不是判在数字上。
    #
    #     viewBox 同理，而且更隐蔽：它一旦和 width/height 不等比，
    #     **本文件里所有按 pt 算的几何判定就集体作废**——字号、线宽、
    #     出血、包围盒，每一个 pt 落纸时都被悄悄缩放了一道。
    def _dim(name):
        raw = root.get(name, "")
        m = re.fullmatch(r"\s*(-?[\d.]+)pt\s*", raw)
        if m:
            return float(m.group(1))
        fails.append(f"根元素 {name}=\"{raw}\" 不是 pt——用户单位一换，"
                     f"落纸尺寸和下面每一条 pt 判定就全错位了")
        return _f(root, name)

    w = _dim("width")
    h = _dim("height")
    if not any(abs(w - v) < 0.5 for v in T.COLUMN.values()):
        fails.append(f"栏宽 {w:.1f}pt 不在版心表内（{ {k: round(v,1) for k,v in T.COLUMN.items()} }）")
    #     高度也得判。图不能比它要落进去的那一页还高，而这一条此前完全
    #     没有：443mm 的单栏图（比 A4 还高 50%）零告警通过。
    col = next((k for k, v in T.COLUMN.items() if abs(w - v) < 0.5), None)
    if col and h > T.PAGE_DEPTH[col] + 0.5:
        fails.append(
            f"图高 {h/T.MM:.0f}mm 超过 {col} 档的页面高度 "
            f"{T.PAGE_DEPTH[col]/T.MM:.0f}mm——放不进去。三个诚实做法："
            f"拆成两张 / 换更宽的栏（格子铺得开，高度就降下来）/ 减少类目。")

    vb = [float(x) for x in re.findall(r"-?[\d.]+", root.get("viewBox", ""))]
    if len(vb) != 4:
        fails.append(f"根元素的 viewBox 不是四个数：{root.get('viewBox')!r}")
    elif (abs(vb[0]) > 0.01 or abs(vb[1]) > 0.01
          or abs(vb[2] - w) > 0.01 or abs(vb[3] - h) > 0.01):
        fails.append(f"viewBox {vb} 与 width/height（{w:.3f}×{h:.3f}）对不上——"
                     f"用户单位不再等于 pt，所有按 pt 判的几何都作废")

    # 2 · 字号下限：含 CJK 的文本按 7.5pt 判，纯拉丁按 6.0pt
    for el in root.iter(f"{NS}text"):
        s = "".join(el.itertext())
        size = _f(el, "font-size")
        floor = S.min_size_for(s)
        if size < floor - 0.01:
            kind = "CJK" if S.has_cjk(s) else "拉丁"
            fails.append(f"字号 {size}pt < {kind} 下限 {floor}pt：{s[:18]!r}")

    # 3 · 文本不得出血。按实测宽度和 anchor 算真实包围盒。
    for el in root.iter(f"{NS}text"):
        s = "".join(el.itertext())
        size, x = _f(el, "font-size"), _f(el, "x")
        tw = S.text_width(s, size)
        anchor = el.get("text-anchor", "start")
        left = x - tw if anchor == "end" else (x - tw / 2 if anchor == "middle" else x)
        if left < -0.5 or left + tw > w + 0.5:
            fails.append(f"文本出血（{left:.1f}→{left+tw:.1f} 超出 0→{w:.1f}）：{s[:18]!r}")

    # 5.1 · 声明了底色的文字，其包围盒必须真的落在那块底色里。
    #      白字飘出深色块半个字，灰度审阅时看不出来，只能靠机器判。
    for el in root.iter(f"{NS}text"):
        box = el.get("data-on-box")
        if not box:
            continue
        bx, by, bw, bh = (float(v) for v in box.split(","))
        st = "".join(el.itertext())
        size, tx, ty = _f(el, "font-size"), _f(el, "x"), _f(el, "y")
        tw = S.text_width(st, size)
        anchor = el.get("text-anchor", "start")
        left = tx - tw if anchor == "end" else (tx - tw / 2 if anchor == "middle" else tx)
        # y 是基线。CJK 字面顶约在基线上方 0.88em，底约在下方 0.12em。
        top_y, bot_y = ty - size * 0.88, ty + size * 0.12
        if (left < bx - 0.5 or left + tw > bx + bw + 0.5
                or top_y < by - 0.5 or bot_y > by + bh + 0.5):
            fails.append(f"文字超出其声明的底色块：{st[:14]!r} "
                         f"({left:.1f}→{left+tw:.1f}) 不在 ({bx:.1f}→{bx+bw:.1f}) 内")

    # 4 · 线宽地板：0.35pt 以下胶印和激光打印都会断线
    for el in root.iter():
        sw = el.get("stroke-width")
        if sw and _f(el, "stroke-width") < T.STROKE["hairline"] - 0.001:
            fails.append(f"线宽 {sw}pt < 印刷地板 {T.STROKE['hairline']}pt")

    # 5 · 文字对其真实底色的对比度。深色格里的数字坐在格子上而不是纸上，
    #     由 data-on 声明底色；不声明就按坐在纸上判。印刷不留情，用 AA 的 4.5:1。
    for el in root.iter(f"{NS}text"):
        fill = el.get("fill", "#000000")
        ground = el.get("data-on") or T.PAPER
        if fill.startswith("#") and ground.startswith("#") and contrast(fill, ground) < 4.5:
            s = "".join(el.itertext())
            fails.append(f"文字对比度 {contrast(fill, ground):.1f}:1 < 4.5（底色 {ground}）："
                         f"{fill} {s[:14]!r}")

    # 6 · 数据色必须两两在灰度上分得开（≥10 L*，感知均匀尺度）
    #     必须两两全比，不能只比在文档里前后相邻的两个：同样三个颜色，
    #     中间夹一个别的颜色，「相邻」就换了对象，结论跟着翻——那是运气不是判定。
    #     差 0 也要报：两个不同色值落在同一明度上，影印后就是同一个灰。
    #     fill 和 stroke 都要收。S1 日序条码、S2 细线族、D1 阶梯直方的数据
    #     **全部编码在 stroke 上**——只收 fill 的话，这三张图等于没进过这条
    #     判定，而它们恰恰是最依赖「几条灰线分不分得开」的那几张。
    fills = []
    for el in root.iter():
        if el.tag == f"{NS}text":
            continue
        for attr in ("fill", "stroke"):
            f = el.get(attr)
            if f and f.startswith("#") and f.upper() != "#FFFFFF":
                if f.upper() not in fills:  # 按大写去重，免得 #1f1f1f 和 #1F1F1F 自己跟自己比
                    fills.append(f.upper())
    for i in range(len(fills)):
        for j in range(i + 1, len(fills)):
            d = abs(lstar(fills[i]) - lstar(fills[j]))
            if d < 10:
                fails.append(f"灰度过近：{fills[i]} vs {fills[j]}（差 {d:.1f} L* < 10）")

    # 7 · 印刷产物里不该有的东西。
    #     SKILL.md 第四节把「3D、阴影、渐变、发光」写进了拒绝清单，但清单
    #     只拦得住照着做的人。这些东西在印刷上要么变成一片灰糊，要么逼出
    #     一次额外套印，所以按标签名逐个点名——正则查 `<image\b` 那种写法
    #     漏得太多：`<linearGradient>` 不叫 image 也不叫 animate。
    BANNED_TAGS = {
        "image": "光栅图——矢量产物里放大会糊",
        "linearGradient": "线性渐变——印刷上是网点渐变，缩印后成一片灰",
        "radialGradient": "径向渐变——同上，且更容易露出色阶断层",
        "filter": "滤镜——RIP 不保证支持，落纸结果不可预期",
        "feGaussianBlur": "高斯模糊——印刷没有「模糊」这个墨",
        "feDropShadow": "投影——SKILL.md 第四节明确拒绝",
        "pattern": "图案填充——缩印后必然摩尔纹",
        "mask": "蒙版——展平后常出白边",
        "animate": "动画——印刷产物里没有动画这回事",
        "animateTransform": "动画——同上",
        "animateMotion": "动画——同上",
        "set": "动画——同上",
    }
    for el in root.iter():
        tag = el.tag.replace(NS, "")
        if tag in BANNED_TAGS:
            fails.append(f"含 <{tag}>：{BANNED_TAGS[tag]}")
            break
    if re.search(r"@keyframes|animation\s*:", src):
        fails.append("样式里含动画——印刷产物里没有动画这回事")
    # 渐变/滤镜也可以只从属性侧混进来（fill="url(#g)"），标签判不到。
    for el in root.iter():
        for attr in ("fill", "stroke"):
            v = el.get(attr, "")
            if v.startswith("url("):
                fails.append(f"{attr}=\"{v}\" 指向了渐变或图案——印刷只接受实色")
                break
        if el.get("filter") or el.get("mix-blend-mode"):
            fails.append("用了 filter / mix-blend-mode——落纸结果由 RIP 决定，不可控")
            break
    # 低透明度：印刷上 alpha 要靠网点模拟，15% 以下基本等于没印。
    # 用 alpha 表达密度是屏幕的做法，纸上应当改半径或改空心点。
    for el in root.iter():
        for attr in ("opacity", "fill-opacity", "stroke-opacity"):
            v = el.get(attr)
            if v is not None and _f(el, attr, 1.0) < 0.15:
                fails.append(f"{attr}={v} < 0.15——这么淡的网点胶印基本落不上纸")
                break

    # 9 · 坐在纸上的文字只许用文字安全档（GRAY[0..3]）。
    #     坐在深色格上的文字走第 5 条的对比度判定，不受这条约束。
    safe = set(c.upper() for c in ramp[:T.TEXT_SAFE_MAX + 1])
    for el in root.iter(f"{NS}text"):
        if el.get("data-on"):
            continue
        f = (el.get("fill") or "").upper()
        if f.startswith("#") and f not in safe:
            fails.append(f"文字用了填充档色 {f}——纸上的文字只许 {pname} 色板的 "
                         f"0..{T.TEXT_SAFE_MAX} 级")
            break

    # 10 · 同一基线上的文字不得互相压字。
    #      x 轴标签抽稀、线端标签避让、峰值标注防重叠——这些逻辑都在图型
    #      内部，出了错没人看得见。尤其是按字符数估宽的抽稀：中西混排下
    #      「W10」字符最多而「周一」最宽，按字符数留位就是留不够，
    #      标签当场叠在一起。这条把那类错误从「目视」挪到机器判。
    lines = []
    for el in root.iter(f"{NS}text"):
        st = "".join(el.itertext())
        size = _f(el, "font-size")
        tx, ty = _f(el, "x"), _f(el, "y")
        tw = S.text_width(st, size)
        anchor_ = el.get("text-anchor", "start")
        left = tx - tw if anchor_ == "end" else (tx - tw / 2 if anchor_ == "middle" else tx)
        lines.append((ty, left, left + tw, st))
    hits = 0
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            yi, li, ri, si_ = lines[i]
            yj, lj, rj, sj_ = lines[j]
            if abs(yi - yj) > 1.0:        # 只比同一基线，错行的重叠是正常排布
                continue
            ov = min(ri, rj) - max(li, lj)
            if ov > 0.5:
                hits += 1
                if hits <= 3:             # 一撞往往连撞一片，报前三处足够定位
                    fails.append(f"同基线文字压字 {ov:.1f}pt @y={yi:.1f}："
                                 f"{si_[:12]!r} 与 {sj_[:12]!r}")
    if hits > 3:
        fails.append(f"……同基线压字共 {hits} 处（只列前 3 处）")

    # 11 · 四件套齐全。SKILL.md 第三节写的是「缺一返工」，那就得能判。
    #      靠字号反推是不行的：来源行和轴标签同为 7.5pt，副题和别的 9pt 文本
    #      也分不开。所以 canvas() 给三个槽位打 data-slot，这里据此点名。
    slots = {el.get("data-slot") for el in root.iter(f"{NS}text")}
    NAMES = {"title": "图题（一句结论）", "subtitle": "副题（口径 · 单位 · 时间范围）",
             "source": "来源行（数据来源 · 样本量）"}
    for key, cn in NAMES.items():
        if key not in slots:
            fails.append(f"四件套缺「{cn}」——读者不看代码，只看这几行")

    # 12 · 数值不得排成科学计数法。`f"{v:,g}"` 在 |v| ≥ 1e6 时会切过去，
    #      于是研报里的营收印成「1.23457e+07」。这是本项目最怕的那一类错：
    #      字号、字色、宽度、对比度全部合规，校验器原本一条都判不出来，
    #      只有拿到纸的人知道这张图作废了。改数值格式化很容易，
    #      难的是让它不再漂回去——所以判在产物上，不判在调用点上。
    for el in root.iter(f"{NS}text"):
        s = "".join(el.itertext())
        m = re.search(r"\d[eE][+-]\d", s)
        if m:
            fails.append(f"数值排成了科学计数法：「{s}」——印刷图里没人读 e+06，"
                         f"用 charts._data.num()")
            break

    # 13 · 几何必须落在版心里，点不得小于印刷地板。
    #
    #      这是校验器此前最大的一块盲区：**除了一条全局线宽地板，
    #      非文字图元的几何一条都没判过。** 于是 `<rect width="0">`
    #      （数值被吞成零长条）、跑到纸外的条、比纸还高的图，全部零告警
    #      通过——文字那边有出血、压字、对比度、底色四道判定，
    #      图形这边一道也没有，而图形才是这张图的主体。
    #
    #      判到 ±0.5pt 的容差：描边跨在路径两侧，半个线宽的溢出是正常的。
    over = []
    for el in root.iter():
        tag = el.tag.replace(NS, "")
        if tag == "text":
            continue                    # 文字有第 3 条按实测宽度专判
        box = _box(el, tag)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        d = max(-x0, -y0, x1 - w, y1 - h)
        if d > 0.5:
            over.append(f"<{tag}> 越出版心 {d:.1f}pt"
                        f"（{x0:.1f},{y0:.1f}→{x1:.1f},{y1:.1f} 不在 {w:.1f}×{h:.1f} 内）")
    for m in over[:3]:
        fails.append(m)
    if len(over) > 3:
        fails.append(f"……几何越界共 {len(over)} 处（只列前 3 处）")

    # 实心点小于 DOT.min_r 时激光打印会丢、胶印会虚。这个 token 此前
    # 在校验器里一次都没被引用过——没有调用点的地板不是地板。
    for el in root.iter(f"{NS}circle"):
        r = _f(el, "r")
        if r < T.DOT["min_r"] - 1e-9:
            fails.append(f"点半径 {r}pt < 印刷地板 {T.DOT['min_r']}pt——胶印会虚、激光会丢")
            break

    # 8 · 字体栈必须中西分家（拉丁在前、CJK 在后，靠逐字符 fallback）
    for el in root.iter(f"{NS}text"):
        fam = el.get("font-family", "")
        if fam and not re.search(r"PingFang|Source Han|Noto (Sans|Serif) SC|Hiragino|Songti", fam):
            fails.append(f"字体栈缺 CJK 兜底：{fam[:40]}")
            break
    return fails


def check_tokens():
    """守住 token 自身的不变量。改 token 比改图更容易悄悄破坏全局。"""
    fails = []
    for k, c in enumerate(T.HEAT):
        want = T.PAPER if k >= T.HEAT_FLIP else T.GRAY[0]
        got = contrast(want, c)
        if got < 4.5:
            fails.append(f"HEAT[{k}]={c} 上的文字（{want}）对比度 {got:.2f}:1 < 4.5"
                         f"——该档落进了 L*50–56 死区，换一档")
    for i in range(len(T.GRAY) - 1):
        d = abs(lstar(T.GRAY[i]) - lstar(T.GRAY[i + 1]))
        if d < 10:
            fails.append(f"GRAY[{i}] 与 GRAY[{i+1}] 只差 {d:.1f} L*，印出来分不开")
    import palettes
    for name in palettes.PRESETS:
        for m in palettes.audit(name):
            fails.append(m)
    for k, v in T.SIZE.items():
        if v < T.MIN_CJK_PT:
            fails.append(f"SIZE['{k}']={v}pt 低于 CJK 下限 {T.MIN_CJK_PT}pt——"
                         f"含中文时会被静默抬高，所有按此值算的宽度都会偏小")
    for i, c in enumerate(T.GRAY[:T.TEXT_SAFE_MAX + 1]):
        if contrast(c, T.PAPER) < 4.5:
            fails.append(f"GRAY[{i}]={c} 号称文字安全档，但对纸只有 "
                         f"{contrast(c, T.PAPER):.2f}:1")

    # PLOT_ASPECT 里不许留没人用的档。前一版的 RATIO 就是这么死的：
    # 声明了四档高宽比，全项目零引用，于是宽栏图被压成扁带也没人拦。
    # token 一旦没有调用点，就不再受任何测试保护，只会慢慢和现实脱节。
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    used = set()
    chart_dir = os.path.join(root, "charts")
    for fn in sorted(os.listdir(chart_dir)):
        if fn.endswith(".py"):
            body = open(os.path.join(chart_dir, fn), encoding="utf-8").read()
            used |= set(re.findall(r'plot_height\([^)]*?["\'](\w+)["\']\s*\)', body))
    for kind in T.PLOT_ASPECT:
        if kind not in used:
            fails.append(f"PLOT_ASPECT['{kind}'] 没有任何图型在用——"
                         f"没有调用点的 token 不受测试保护，删掉或接上")
    for kind in used - set(T.PLOT_ASPECT):
        fails.append(f"有图型调用了 plot_height(..., '{kind}')，但 PLOT_ASPECT 里没有这一档")
    if T.PLOT_H["min"] >= T.PLOT_H["max"]:
        fails.append(f"PLOT_H 上下限反了：min={T.PLOT_H['min']} ≥ max={T.PLOT_H['max']}")
    return fails


def check_catalog(src=None):
    """目录声明的张数必须等于实际有实现的行数。

    这类数字漂移是文档腐坏最常见的入口——声明写在标题里，实现散在表格里，
    改了一处忘了另一处。能机器判就别指望人记得。

    src 可注入 catalog.md 的正文，供反例测试喂一份故意写坏的目录。
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if src is None:
        src = open(os.path.join(root, "catalog.md"), encoding="utf-8").read()
    declared = re.search(r"^#[^\n]*·\s*(\d+)\s*张", src, re.M)
    rows = re.findall(r"^\|\s*([RSCDM]\d+)\s*\|.*\|\s*`([^`]+)`\s*\|\s*$", src, re.M)
    fails = []
    if not declared:
        return ["catalog.md 标题缺少「· N 张」声明"]
    if int(declared.group(1)) != len(rows):
        fails.append(f"catalog.md 声明 {declared.group(1)} 张，实际有实现的是 {len(rows)} 行")
    for num, impl in rows:
        if not os.path.exists(os.path.join(root, impl)):
            fails.append(f"catalog.md {num} 指向的实现不存在：{impl}")
        else:
            body = open(os.path.join(root, impl), encoding="utf-8").read()
            if f"# ════ {num} " not in body:
                fails.append(f"{impl} 缺少 `# ════ {num} 图名 ════` 标记块")

    # 分区标题挂着「待建」，底下却已经有实现——这是文档腐坏最典型的样子：
    # 建完了忘了摘标记，读者按标题以为这一族还没做。四个 S/C/D/M 分区
    # 全都挂了半年多才被发现，正因为没人机器判。
    section = None
    built = {}
    for line in src.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            section = m.group(1).strip()
            built.setdefault(section, [False, "待建" in section])
        elif section and re.match(r"^\|\s*[RSCDM]\d+\s*\|.*`[^`]+`\s*\|\s*$", line):
            built[section][0] = True
    for name, (has_impl, marked) in built.items():
        if has_impl and marked:
            fails.append(f"catalog.md 分区「{name}」标着「待建」，底下却已经有实现了")

    # 「类目上限」列里写了数字，就必须标「代码强制」。
    # 一张表里七条标了「代码强制」、两条没标，读者根本分不清哪条会真拦——
    # 而没被代码兜住的那两条，迟早会有人越过去。声明和实现的漂移
    # 正是这类文档最先烂掉的地方，所以让它机器判。
    for line in src.splitlines():
        if not re.match(r"^\|\s*[RSCDM]\d+\s*\|", line):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 8:
            fails.append(f"catalog.md 行列数不对，无法核对上限：{line[:40]}")
            continue
        num, cap = cells[1], cells[5]
        if re.search(r"\d", cap) and "代码强制" not in cap:
            fails.append(
                f"catalog.md {num} 的类目上限「{cap}」写了数字却没标「代码强制」——"
                f"要么在实现里真的拦住并标注，要么把这个数从表里拿掉")
    return fails


def check_docs(readme=None, root=None):
    """README 里对别的文件的数字声明必须成立。

    「SKILL.md # 决策规则，108 行」这类数字是有信息量的——一份决策文档
    涨到三百行就已经失败了——但它同时是最容易漂的东西：改了 SKILL.md
    没人会想起回头改 README。这两轮修 bug 就把它手动同步了两次，
    第三次一定会忘。能机器判就别指望人记得。

    readme / root 可注入，供反例测试喂一份写坏的 README。
    """
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if readme is None:
        readme = open(os.path.join(root, "README.md"), encoding="utf-8").read()
    fails = []

    claims = re.findall(r"^(\S+\.md)\s+#[^\n]*?(\d+)\s*行", readme, re.M)
    if not claims:
        fails.append("README.md 的结构块里一条「N 行」声明都没有——正则漂了？")
    for fname, n in claims:
        path = os.path.join(root, fname)
        if not os.path.exists(path):
            fails.append(f"README.md 声称 {fname} 有 {n} 行，但这个文件不存在")
            continue
        real = len(open(path, encoding="utf-8").read().splitlines())
        if int(n) != real:
            fails.append(f"README.md 说 {fname} 是 {n} 行，实际 {real} 行")

    # CI 徽标指向的 workflow 文件必须真的存在。徽标坏掉不会报错，
    # 只会永远显示一张「workflow not found」的灰图——而所有人都只当它是
    # 「还没跑完」，于是一块本该显示构建状态的地方长期在撒谎。
    for wf in re.findall(r"github\.com/[\w.-]+/[\w.-]+/actions/workflows/([\w.-]+)/badge\.svg",
                         readme):
        if not os.path.exists(os.path.join(root, ".github", "workflows", wf)):
            fails.append(f"README.md 的 CI 徽标指向 .github/workflows/{wf}，"
                         f"但这个 workflow 不存在")

    # README 的图型表和 catalog 的声明张数必须对得上。两张表各写各的，
    # 加了图只改一处是迟早的事。
    cat = open(os.path.join(root, "catalog.md"), encoding="utf-8").read()
    declared = re.search(r"^#[^\n]*·\s*(\d+)\s*张", cat, re.M)
    rows = re.findall(r"^\|\s*([RSCDM]\d+)\s*\|", readme, re.M)
    if declared and len(rows) != int(declared.group(1)):
        fails.append(f"README.md 的图型表有 {len(rows)} 行，"
                     f"catalog.md 声明 {declared.group(1)} 张——两张表漂开了")
    return fails


USAGE = """用法：python3 scripts/validate.py out/*.svg

SKILL.md 第零节第 8 条把这条命令的退出码当作交付闸门，所以它不给参数时
**必须失败**：glob 匹配不到任何文件（out/ 是空的、或者根本没出图）时，
shell 传进来的就是零个参数。此时若照旧打印「0 个文件，0 项不合格」并
退出 0，闸门就在「一张图都没有」的情况下放行了——而这正是最该拦住的
那种交付。"""


if __name__ == "__main__":
    targets = sys.argv[1:]
    if not targets or targets[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0 if targets[:1] in (["-h"], ["--help"]) else 2)
    # 仓库自检（tokens / catalog / README）只在校验本仓自己的产物时跑。
    # 用户在自己的项目里验自己的图，前三行却是 inkstone 的 README 体检——
    # 这三行对他毫无意义，而且他若只拷了 charts/ + tokens.py，check_docs()
    # 会直接 FileNotFoundError。按目标是否落在本仓内自动判，不用他记一个开关。
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    own = all(os.path.abspath(t).startswith(_root + os.sep) for t in targets)

    total = 0
    if not own:
        print(f"（校验 {len(targets)} 份仓库外的产物，跳过 inkstone 自身的体检）")
    tok = check_tokens() if own else []
    if own:
        print("✓ tokens.py" if not tok else "✗ tokens.py")
    for f in tok:
        print(f"    {f}")
    total += len(tok)
    cat = check_catalog() if own else []
    if own:
        print("✓ catalog.md" if not cat else "✗ catalog.md")
    for f in cat:
        print(f"    {f}")
    total += len(cat)
    doc = check_docs() if own else []
    if own:
        print("✓ README.md" if not doc else "✗ README.md")
    for f in doc:
        print(f"    {f}")
    total += len(doc)
    for p in targets:
        # 一份读不了或解析不了的产物，不能把后面几十份的检查一起带走。
        # 裸 traceback 还有个更坏的地方：退出码非零，看起来像「校验器
        # 拦下了什么」，实际是它自己死在第一份上，剩下的一份都没查。
        try:
            fails = check(p)
        except FileNotFoundError:
            fails = [f"文件不存在——glob 没匹配上？先跑 python3 demo.py"]
        except ET.ParseError as e:
            fails = [f"不是合法的 SVG：{e}"]
        except Exception as e:
            fails = [f"校验时抛了 {type(e).__name__}: {e}——这份产物没有被检查"]
        total += len(fails)
        mark = "✗" if fails else "✓"
        print(f"{mark} {p}")
        for f in fails:
            print(f"    {f}")
    print(f"\n{len(targets)} 个文件，{total} 项不合格")
    sys.exit(1 if total else 0)
