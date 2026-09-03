# -*- coding: utf-8 -*-
"""SVG → PDF / PNG@300dpi。矢量走 rsvg-convert，字体在 PDF 里嵌入为路径。"""
import subprocess, sys, os, shutil

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
            made.append(dst)
    else:
        print("警告：未找到 rsvg-convert，只产出 SVG。brew install librsvg", file=sys.stderr)
    return made
