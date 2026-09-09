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

    # 1 · 栏宽必须落在版心表里。图不能想多宽多宽，宽度由载体决定。
    w = float(re.sub(r"[a-z]+$", "", root.get("width", "0")))
    if not any(abs(w - v) < 0.5 for v in T.COLUMN.values()):
        fails.append(f"栏宽 {w:.1f}pt 不在版心表内（{ {k: round(v,1) for k,v in T.COLUMN.items()} }）")

    # 2 · 字号下限：含 CJK 的文本按 7.5pt 判，纯拉丁按 6.0pt
    for el in root.iter(f"{NS}text"):
        s = "".join(el.itertext())
        size = float(el.get("font-size", "0"))
        floor = S.min_size_for(s)
        if size < floor - 0.01:
            kind = "CJK" if S.has_cjk(s) else "拉丁"
            fails.append(f"字号 {size}pt < {kind} 下限 {floor}pt：{s[:18]!r}")

    # 3 · 文本不得出血。按实测宽度和 anchor 算真实包围盒。
    for el in root.iter(f"{NS}text"):
        s = "".join(el.itertext())
        size, x = float(el.get("font-size", "0")), float(el.get("x", "0"))
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
        size, tx, ty = float(el.get("font-size", "0")), float(el.get("x", "0")), float(el.get("y", "0"))
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
        if sw and float(sw) < T.STROKE["hairline"] - 0.001:
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
    fills = []
    for el in root.iter():
        f = el.get("fill")
        if f and f.startswith("#") and f.upper() != "#FFFFFF" and el.tag != f"{NS}text":
            if f.upper() not in fills:      # 按大写去重，免得 #1f1f1f 和 #1F1F1F 自己跟自己比
                fills.append(f.upper())
    for i in range(len(fills)):
        for j in range(i + 1, len(fills)):
            d = abs(lstar(fills[i]) - lstar(fills[j]))
            if d < 10:
                fails.append(f"灰度过近：{fills[i]} vs {fills[j]}（差 {d:.1f} L* < 10）")

    # 7 · 印刷产物里不该有的东西
    if root.iter(f"{NS}image").__next__() if False else re.search(r"<image\b", src):
        fails.append("含 <image> 光栅图——矢量产物里不允许，放大会糊")
    if re.search(r"<animate|@keyframes|animation\s*:", src):
        fails.append("含动画——印刷产物里没有动画这回事")

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
        size = float(el.get("font-size", "0"))
        tx, ty = float(el.get("x", "0")), float(el.get("y", "0"))
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


if __name__ == "__main__":
    targets = sys.argv[1:] or []
    total = 0
    tok = check_tokens()
    print("✓ tokens.py" if not tok else "✗ tokens.py")
    for f in tok:
        print(f"    {f}")
    total += len(tok)
    cat = check_catalog()
    print("✓ catalog.md" if not cat else "✗ catalog.md")
    for f in cat:
        print(f"    {f}")
    total += len(cat)
    for p in targets:
        fails = check(p)
        total += len(fails)
        mark = "✗" if fails else "✓"
        print(f"{mark} {p}")
        for f in fails:
            print(f"    {f}")
    print(f"\n{len(targets)} 个文件，{total} 项不合格")
    sys.exit(1 if total else 0)
