#!/usr/bin/env python3
"""Draws vst/images/wordmark.svg: "profit '8" set in an uncial (biblical manuscript) face and converted to outlines, so the SVG needs no font.

    make_wordmark.py FONT.ttf [OUT.svg]

The face used is Almendra (SIL Open Font License 1.1, https://github.com/google/fonts/tree/main/ofl/almendra; Uncial Antiqua, ofl/uncialantiqua, is the heavier alternative); only the
glyph outlines of the letters used are embedded, which the OFL allows. Needs fontTools."""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

def run(font_path, out, text=("profit", "'08"), size=86, tracking=2):
    f = TTFont(font_path)
    gs, cmap, upm = f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm
    k = size / upm
    x, parts = 10.0, []
    base = 74
    for part, fill in ((text[0], "#f2f2f4"), (text[1], "#e5261b")):
        d = []
        for ch in part:
            g = gs[cmap[ord(ch)]]
            pen = SVGPathPen(gs)
            g.draw(TransformPen(pen, (k, 0, 0, -k, x, base)))
            d.append(pen.getCommands())
            x += g.width * k + tracking
        parts.append('<path d="%s" fill="%s"/>' % (" ".join(d), fill))
        x += 14
    w = int(x)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="124" viewBox="0 0 360 124">
<g>{"".join(parts)}</g>
<path d="M12,98 C120,92 260,104 {346},96" fill="none" stroke="#e5261b" stroke-width="1.6" stroke-linecap="round" opacity="0.85"/>
<text x="180" y="118" text-anchor="middle" font-family="Titillium Web, sans-serif" font-weight="600" font-size="11" letter-spacing="3.6" fill="#9c9ca6">8 VOICE ANALOG SYNTHESIZER</text>
</svg>
'''
    open(out, "w").write(svg)

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "vst/images/wordmark.svg")
