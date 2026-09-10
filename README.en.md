# Inkstone · Print-first charts for Chinese documents

[![ci](https://github.com/wuzhenhua24/inkstone/actions/workflows/ci.yml/badge.svg)](https://github.com/wuzhenhua24/inkstone/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![deps](https://img.shields.io/badge/dependencies-0-black)
[![license](https://img.shields.io/badge/license-MIT-black)](LICENSE)
· 中文：[README.md](README.md)

Charts measured in **points, not pixels**. Width is not a style choice — it comes
from a journal column table, so the figure lands 1:1 on paper. Vector SVG, PDF and
300dpi PNG; no JavaScript runtime; drops straight into Word, LaTeX, InDesign and
slides. **Pure standard library, zero dependencies.**

![urbanisation](docs/gallery/ex3-urbanization.png)

## What is actually different

Most of the print rules are enforced **at construction** — a caller cannot violate
them. `_svg.text()` raises the font size to the CJK floor before it emits anything,
and every chart with a category cap raises `ValueError` rather than drawing a figure
too crowded to read. The validator covers what construction cannot: text bleeding
past the column, geometry outside the page box, two data greys closer than 10 L\*,
labels colliding on a shared baseline, gradients and filters that offset printing
cannot reproduce.

| | Screen charting | Inkstone |
|---|---|---|
| Unit | px, scaled by DPR | **pt**, 1:1 on paper |
| Width | responsive | **from a column table** — 85 / 114 / 170 / 156 / 254 mm |
| CJK type size | no floor | **7.5pt floor**, raised in code, not by convention |
| Stroke | 0.5px hairlines look great | **0.35pt floor** — thinner breaks in offset printing |
| Colour | anything | **CIE L\* ladder**; colour tiers change hue, never lightness |
| Animation | a selling point | does not exist |
| Rule enforcement | a style guide and good intentions | `scripts/validate.py`, exit code gates delivery |

Two consequences worth spelling out:

**Photocopy safety.** Every colour tier moves the seven-step grey ladder onto a
single hue, so lightness is unchanged. A colour figure photocopied to black and
white is the *same figure* as the mono version — 13 charts × 3 tiers = 39
combinations, largest measured deviation 0.4 L\*. Single-hue lightness ladders do
not rely on hue discrimination, so this is colour-blind safe by construction rather
than by a palette lookup.

**Mixed CJK/Latin label widths.** Label placement is computed per character from
Unicode East Asian Width: CJK glyphs as full ems, Latin deliberately over-estimated.
Estimating by character count gets it wrong in both directions — in `["周一", "W10"]`
the *longer* string is the narrower one. The middle dot `·` is the sharp case: 0.278em
in Helvetica Neue, 1.000em in Hiragino Sans GB, measured from the fonts' `hmtx`
tables. SVG falls back per character, so the same file is a different width on a
machine with Inter than on one with only Noto CJK. Print cannot control the RIP's
font set, so the wider value is always assumed.

## Install

Three paths, depending on what you want.

**As a Claude Code skill** — the repository *is* the skill; `SKILL.md` sits at root:

```bash
git clone https://github.com/wuzhenhua24/inkstone ~/.claude/skills/inkstone
```

**As a Python library** — nothing to install, just put it on `sys.path`:

```python
import sys; sys.path.insert(0, "/path/to/inkstone")   # or set PYTHONPATH
from charts.rank_bars import rank_bars
from scripts.render import render

svg = rank_bars([("华东", 128), ("华北", 96), ("华南", 71)],
                title="华东最高，是华南的 1.8 倍",
                subtitle="2026 上半年 · 单位：万元",
                source="数据来源：内部财务", unit="万元")
render(svg, "mine", outdir=".")      # -> mine.svg + mine.pdf + mine.png@300dpi
```

**For the rules only** — read [SKILL.md](SKILL.md) and [catalog.md](catalog.md).
Both are in Chinese; the code and its guards are the executable version of them.

PDF/PNG export needs `librsvg` (`brew install librsvg`, `apt install librsvg2-bin`).
SVG alone needs nothing.

> The `inkstone` on PyPI is an unrelated RCWA electromagnetic solver. This project
> is distributed as a directory and is not published to PyPI.

## Gate your own build

```bash
python3 scripts/validate.py out/*.svg
```

| Exit | Meaning |
|---|---|
| `0` | every artefact passes |
| `1` | something failed, or a file could not be read |
| `2` | no arguments — an unmatched glob means nothing was rendered, which must not pass |

Running it on files outside this repository skips Inkstone's own self-checks.

```yaml
- run: python3 demo.py && python3 scripts/validate.py out/*.svg
```

## Chart types

Thirteen, across five families — comparison/ranking, time series, composition,
distribution, relationship. Data shape is the primary key for choosing: the catalogue
lists each one's shape, carrier, category cap and failure conditions.
See [catalog.md](catalog.md), and [examples/](examples/README.md) for three finished
figures built on real World Bank data.

## Licence

[MIT](LICENSE). Independent implementation; no third-party charting code.
