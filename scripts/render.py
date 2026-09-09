# -*- coding: utf-8 -*-
"""SVG → PDF / PNG@300dpi。矢量走 rsvg-convert，字体在 PDF 里嵌入为路径。"""
import os, shutil, struct, subprocess, sys, zlib

_M_PER_INCH = 0.0254   # PNG 的 pHYs 块按「每米像素数」记分辨率


def _chunk(typ, data):
    return (struct.pack(">I", len(data)) + typ + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))


def stamp_png_dpi(path, dpi):
    """把分辨率写进 PNG 的 pHYs 块。

    rsvg-convert 的 --dpi-x/--dpi-y 只决定栅格化时算出多少像素，**不往
    文件里写分辨率**。产出的 PNG 因此不带 pHYs 块：像素数是对的
    （85mm @300dpi = 1004px），但 Word / InDesign / LaTeX 读不到 dpi
    就一律按 72dpi 解释——同一张图置入时放大 4.17 倍（85mm 变成 354mm），
    用户得手动缩到 24%，还会以为这是张低分图。

    「300dpi PNG，直接置入 Word」这句承诺，差的就是这 9 个字节。
    pHYs 必须落在 IHDR 之后、IDAT 之前；已有的一律丢掉重写，
    免得不同版本的 rsvg 各写各的。
    """
    with open(path, "rb") as f:
        raw = f.read()
    sig = b"\x89PNG\r\n\x1a\n"
    if not raw.startswith(sig):
        raise ValueError(f"{path} 不是 PNG，写不进分辨率块")
    ppm = int(round(dpi / _M_PER_INCH))
    phys = _chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1))
    out, i = [sig], len(sig)
    while i < len(raw):
        ln = struct.unpack(">I", raw[i:i + 4])[0]
        typ = raw[i + 4:i + 8]
        end = i + 12 + ln
        if typ != b"pHYs":
            out.append(raw[i:end])
        if typ == b"IHDR":
            out.append(phys)
        i = end
    with open(path, "wb") as f:
        f.write(b"".join(out))
    return path


def render(svg_text, stem, outdir="out", png_dpi=300):
    os.makedirs(outdir, exist_ok=True)
    svg_path = os.path.join(outdir, stem + ".svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_text)
    made = [svg_path]
    if shutil.which("rsvg-convert"):
        for fmt, extra in (("pdf", []), ("png", ["--dpi-x", str(png_dpi), "--dpi-y", str(png_dpi)])):
            dst = os.path.join(outdir, f"{stem}.{fmt}")
            subprocess.run(["rsvg-convert", "-f", fmt, "-o", dst, *extra, svg_path], check=True)
            if fmt == "png":
                stamp_png_dpi(dst, png_dpi)
            made.append(dst)
    else:
        print("警告：未找到 rsvg-convert，只产出 SVG。brew install librsvg", file=sys.stderr)
    return made
