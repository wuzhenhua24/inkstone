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

    # 6 · 相邻数据色必须在灰度上分得开（≥10 L*，感知均匀尺度）
    fills = []
    for el in root.iter():
        f = el.get("fill")
        if f and f.startswith("#") and f.upper() not in ("#FFFFFF",) and el.tag != f"{NS}text":
            if f not in fills:
                fills.append(f)
    for i in range(len(fills) - 1):
        d = abs(lstar(fills[i]) - lstar(fills[i + 1]))
        if 0 < d < 10:
            fails.append(f"灰度过近：{fills[i]} vs {fills[i+1]}（差 {d:.1f} L* < 10）")

    # 7 · 印刷产物里不该有的东西
    if root.iter(f"{NS}image").__next__() if False else re.search(r"<image\b", src):
        fails.append("含 <image> 光栅图——矢量产物里不允许，放大会糊")
    if re.search(r"<animate|@keyframes|animation\s*:", src):
        fails.append("含动画——印刷产物里没有动画这回事")

    # 9 · 坐在纸上的文字只许用文字安全档（GRAY[0..3]）。
    #     坐在深色格上的文字走第 5 条的对比度判定，不受这条约束。
    safe = set(c.upper() for c in T.GRAY[:T.TEXT_SAFE_MAX + 1])
    for el in root.iter(f"{NS}text"):
        if el.get("data-on"):
            continue
        f = (el.get("fill") or "").upper()
        if f.startswith("#") and f not in safe:
            fails.append(f"文字用了填充档灰 {f}——纸上的文字只许 GRAY[0..{T.TEXT_SAFE_MAX}]")
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
    for i, c in enumerate(T.GRAY[:T.TEXT_SAFE_MAX + 1]):
        if contrast(c, T.PAPER) < 4.5:
            fails.append(f"GRAY[{i}]={c} 号称文字安全档，但对纸只有 "
                         f"{contrast(c, T.PAPER):.2f}:1")
    return fails


def check_catalog():
    """目录声明的张数必须等于实际有实现的行数。

    这类数字漂移是文档腐坏最常见的入口——声明写在标题里，实现散在表格里，
    改了一处忘了另一处。能机器判就别指望人记得。
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
