#!/usr/bin/env python3
"""Profit-08 2 skin art library (Pillow, drawn from code): the released 0.1.x look -- a brushed charcoal plate between wood cheeks,
pale rounded section frames with caps titles, black pointer knobs with an amber arc, amber LEDs, amber-on-red pick fields and a red
dot-matrix display. The wordmark and cheeks are rendered from the released SVGs in vst/images (cairosvg); the plate's brushed noise is
redrawn here (cairosvg ignores SVG filters). Fonts: Titillium Web (OFL, mpc-vst-plugins/tools/html_art/fonts) baked into the art."""
import io, math, os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VST_IMG = os.path.join(ROOT, "vst", "images")
FONT_DIRS = [os.path.join(ROOT, "tools", "fonts"),
             os.path.join(ROOT, "..", "mpc-vst-plugins", "tools", "html_art", "fonts")]

W, H = 1280, 628
INK = (242, 242, 244)
INK_DIM = (190, 190, 198)
LINE = (141, 141, 150)
AMBER = (255, 154, 31)
AMBER_DIM = (74, 42, 6)
RED = (255, 74, 53)
RED_BG = (29, 5, 4)
RED_CELL = (40, 8, 7)
KEY = (191, 192, 200)
KEY_INK = (21, 22, 26)

_fonts = {}


def font(px, weight="SemiBold"):
    k = (px, weight)
    if k not in _fonts:
        for d in FONT_DIRS:
            p = os.path.join(d, "TitilliumWeb-%s.ttf" % weight)
            if os.path.exists(p):
                _fonts[k] = ImageFont.truetype(p, px)
                break
        else:
            raise SystemExit("Titillium Web not found (looked in %s)" % FONT_DIRS)
    return _fonts[k]


def svg(name, w, h):
    import cairosvg
    png = cairosvg.svg2png(url=os.path.join(VST_IMG, name), output_width=w, output_height=h)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def plate(seed=3):
    """The brushed charcoal plate (metal.svg: vertical gradient + horizontal streaks + sheen), with the wood cheeks."""
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    top, mid, bot = (42, 42, 46), (24, 24, 27), (16, 16, 18)
    for y in range(H):
        t = y / (H - 1)
        a, b, u = (top, mid, t * 2) if t < 0.5 else (mid, bot, t * 2 - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)))
    # streaks: per-row noise stretched horizontally
    small = Image.new("L", (48, H))
    small.putdata([rnd.randint(0, 255) for _ in range(48 * H)])
    streak = small.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur((6, 0.4)))
    light = Image.new("RGB", (W, H), (215, 215, 228))
    img = Image.composite(light, img, streak.point(lambda v: max(0, v - 150) // 3))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.composite(dark, img, streak.point(lambda v: max(0, 105 - v) // 2))
    # sheen
    sheen = Image.new("L", (W, 1))
    for x in range(W):
        t = x / (W - 1)
        sheen.putpixel((x, 0), int(255 * max(0.0, 0.07 - abs(t - 0.28) * 0.25, 0.05 - abs(t - 0.78) * 0.25)))
    img = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), img, sheen.resize((W, H)))
    img = img.convert("RGBA")
    img.alpha_composite(svg("cheeks.svg", W, H))
    return img


def frame(img, x, y, w, h, title=None, cap_centre=True):
    """A pale rounded section outline with a caps title (centred: the MPC's Q tag sits at the top-left of a Q-Link group)."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x, y, x + w, y + h], 8, fill=(255, 255, 255, 6), outline=LINE + (255,), width=1)
    img.alpha_composite(ov)
    if title:
        d = ImageDraw.Draw(img)
        f = font(13, "Bold")
        txt = " ".join(title.upper()).replace("   ", "     ")  # letter-spaced caps
        if cap_centre:
            d.text((x + w / 2, y + 18), txt, font=f, fill=INK, anchor="mm")
        else:
            d.text((x + 18, y + 18), txt, font=f, fill=INK, anchor="lm")


def caption(d, cx, y, text, size=12, col=INK, weight="SemiBold"):
    d.text((cx, y), text, font=font(size, weight), fill=col, anchor="mm")


def knob(img, cx, cy, value, r=29, bipolar=False):
    """Black knob, amber value arc (from 7 o'clock, or from 12 for bipolar), white pointer."""
    S = 4
    D = (r + 10) * 2
    k = Image.new("RGBA", (D * S, D * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    c = D * S / 2
    rr = r * S
    sh = Image.new("RGBA", k.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([c - rr, c - rr + 3 * S, c + rr, c + rr + 3 * S], fill=(0, 0, 0, 170))
    k.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3 * S)))
    a0, a1 = 135, 405
    ar = rr + 4 * S
    d.arc([c - ar, c - ar, c + ar, c + ar], a0, a1, fill=(255, 255, 255, 26), width=3 * S)
    va = a0 + (a1 - a0) * value
    if bipolar:
        lo, hi = sorted((270, va))
    else:
        lo, hi = a0, va
    if hi - lo > 0.5:
        d.arc([c - ar, c - ar, c + ar, c + ar], lo, hi, fill=AMBER + (242,), width=3 * S)
    prophet_cap(k, c, rr, va, S)
    k = k.resize((D, D), Image.LANCZOS)
    img.alpha_composite(k, (int(cx - D / 2), int(cy - D / 2)))


def prophet_cap(k, c, R, va, S):
    """The released skin's knob (mpc-vst-plugins html_art knob_prophet): a ribbed black skirt, a silver ring, a brushed black top
    and a white pointer, seen from above. Ribs and brushing turn with the value."""
    d = ImageDraw.Draw(k)
    turn = math.radians(va + 90)          # 0 = pointer straight up
    d.ellipse([c - R, c - R, c + R, c + R], fill=(11, 11, 12, 255))
    n = 34
    for i in range(n):                    # ribs: short radial dashes round the skirt
        t = turn + i * 2 * math.pi / n
        r0, r1 = R - 3.6 * S, R - 0.2 * S
        d.line([(c + r0 * math.sin(t), c - r0 * math.cos(t)), (c + r1 * math.sin(t), c - r1 * math.cos(t))],
               fill=(74, 75, 79, 255), width=int(2.2 * S))
    # silver ring: diagonal metal gradient
    ring = Image.new("RGBA", k.size, (0, 0, 0, 0))
    rg = ImageDraw.Draw(ring)
    Rr = R * 0.83
    for yy in range(int(c - Rr), int(c + Rr) + 1):
        u = (yy - (c - Rr)) / (2 * Rr)
        v = int(max(80, min(230, 215 - 130 * u + 40 * math.sin(u * 6.0))))
        rg.line([(c - Rr, yy), (c + Rr, yy)], fill=(v, v, v + 3, 255))
    m = Image.new("L", k.size, 0)
    ImageDraw.Draw(m).ellipse([c - Rr, c - Rr, c + Rr, c + Rr], fill=255)
    k.paste(ring, (0, 0), m)
    d.ellipse([c - Rr, c - Rr, c + Rr, c + Rr], outline=(138, 140, 144, 255), width=max(1, int(0.6 * S)))
    d.ellipse([c - R * 0.72, c - R * 0.72, c + R * 0.72, c + R * 0.72], fill=(85, 87, 91, 255))
    d.ellipse([c - R * 0.68, c - R * 0.68, c + R * 0.68, c + R * 0.68], fill=(26, 27, 29, 255), outline=(8, 9, 10, 255), width=S)
    for i in range(28):                   # brushed top
        t = turn + i * math.pi / 14
        d.line([(c + R * 0.1 * math.sin(t), c - R * 0.1 * math.cos(t)), (c + R * 0.62 * math.sin(t), c - R * 0.62 * math.cos(t))],
               fill=(52, 54, 58, 200), width=max(1, int(0.5 * S)))
    d.line([(c + R * 0.1 * math.sin(turn), c - R * 0.1 * math.cos(turn)), (c + R * 0.66 * math.sin(turn), c - R * 0.66 * math.cos(turn))],
           fill=(247, 247, 245, 255), width=int(2.6 * S))
    sh = Image.new("RGBA", k.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([c - R * 0.63, c - R * 0.58, c + R * 0.27, c - R * 0.02], fill=(255, 255, 255, 40))
    k.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2 * S)))


def led(img, cx, cy, on, r=11):
    S = 4
    D = (r + 12) * 2
    k = Image.new("RGBA", (D * S, D * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    c = D * S / 2
    if on:
        g = Image.new("RGBA", k.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([c - (r + 6) * S, c - (r + 6) * S, c + (r + 6) * S, c + (r + 6) * S], fill=AMBER + (150,))
        k.alpha_composite(g.filter(ImageFilter.GaussianBlur(5 * S)))
    d.ellipse([c - (r + 2) * S, c - (r + 2) * S, c + (r + 2) * S, c + (r + 2) * S], fill=(14, 14, 16, 255), outline=LINE + (255,), width=S)
    d.ellipse([c - r * S, c - r * S, c + r * S, c + r * S], fill=((255, 165, 31) if on else AMBER_DIM) + (255,))
    d.ellipse([c - r * 0.55 * S, c - r * 0.75 * S, c + r * 0.3 * S, c - r * 0.1 * S], fill=(255, 255, 255, 70 if on else 25))
    img.alpha_composite(k.resize((D, D), Image.LANCZOS), (int(cx - D / 2), int(cy - D / 2)))


def pick(img, cx, cy, w, h, text):
    """Pick-list field: dark red box, amber choice text, amber down triangle (tap opens the drawn list)."""
    d = ImageDraw.Draw(img)
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 5, fill=(26, 6, 5), outline=LINE, width=1)
    px = 17
    while px > 11 and d.textlength(text, font=font(px)) > w - 34:
        px -= 1
    d.text((x0 + (w - 26) / 2 + 2, cy), text, font=font(px, "SemiBold"), fill=AMBER, anchor="mm")
    tx = x0 + w - 18
    d.polygon([(tx - 8, cy - 4), (tx + 8, cy - 4), (tx, cy + 5)], fill=AMBER)


def lcd(img, x, y, w, h, text, arrows=True, align="mm"):
    """Red dot-matrix display in a black bezel, optional grey arrow keys at the ends."""
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + w, y + h], 6, fill=(12, 12, 14))
    ax = 52 if arrows else 8
    ix0, ix1 = x + ax, x + w - ax
    d.rectangle([ix0, y + 6, ix1, y + h - 6], fill=RED_BG)
    for gx in range(int(ix0) + 2, int(ix1), 3):
        d.line([(gx, y + 7), (gx, y + h - 7)], fill=RED_CELL)
    if arrows:
        for sx, dirn in ((x + ax / 2, -1), (x + w - ax / 2, 1)):
            cy = y + h / 2
            d.polygon([(sx - 6 * dirn, cy - 10), (sx - 6 * dirn, cy + 10), (sx + 7 * dirn, cy)], fill=KEY)
    f = font(17, "SemiBold")
    if align == "lm":
        d.text((ix0 + 14, y + h / 2), text, font=f, fill=RED, anchor="lm")
    else:
        d.text(((ix0 + ix1) / 2, y + h / 2), text, font=f, fill=RED, anchor="mm")


def key(img, cx, cy, w, h, text, lit=False):
    """A grey hardware-style key with the caption baked in (the released skin's button colour)."""
    S = 3
    k = Image.new("RGBA", ((w + 8) * S, (h + 10) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.rounded_rectangle([4 * S, 6 * S, (w + 4) * S, (h + 8) * S], 6 * S, fill=(70, 70, 76, 255))
    top = (214, 215, 222) if not lit else (255, 178, 70)
    bot = (170, 171, 180) if not lit else (232, 130, 18)
    cap = Image.new("RGBA", (w * S, h * S))
    cd = ImageDraw.Draw(cap)
    for yy in range(h * S):
        t = yy / (h * S)
        cd.line([(0, yy), (w * S, yy)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    m = Image.new("L", cap.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * S - 1, h * S - 1], 6 * S, fill=255)
    k.paste(cap, (4 * S, 3 * S), m)
    d.line([(10 * S, 4 * S), ((w - 2) * S, 4 * S)], fill=(255, 255, 255, 140), width=S)
    k = k.resize((w + 8, h + 10), Image.LANCZOS)
    img.alpha_composite(k, (int(cx - w / 2 - 4), int(cy - h / 2 - 3)))
    ImageDraw.Draw(img).text((cx, cy), text, font=font(17, "Bold"), fill=KEY_INK, anchor="mm")


def wordmark(img, x, y, w, h):
    img.alpha_composite(svg("wordmark.svg", w, h), (x, y))


def qlink_overlay(img, rect):
    """Preview only: the MPC's Q-Link bounds overlay (a dashed rectangle per group of four)."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = rect
    col = (80, 200, 255)
    for xa in range(int(x0), int(x1), 12):
        d.line([(xa, y0), (min(xa + 6, x1), y0)], fill=col, width=2)
        d.line([(xa, y1), (min(xa + 6, x1), y1)], fill=col, width=2)
    for ya in range(int(y0), int(y1), 12):
        d.line([(x0, ya), (x0, min(ya + 6, y1))], fill=col, width=2)
        d.line([(x1, ya), (x1, min(ya + 6, y1))], fill=col, width=2)
