#!/usr/bin/env python3
"""Write skins/TUI.json + skins/Q-Links.json (the MPC's native skin) and the PNGs they use, from tools/skin_pages.py.
Structure from JV-880 2.0 / Dexed 2.0 (tools/make_tui.py there): reusable knob and display-field components, LED Buttons, drawn
pick-lists (the native MenuOverlay opens empty for an external VST2), Labels for live text, one Q-Link group
of four per printed section, sub-tabs where a page has more than four groups.

    python3 tools/make_tui.py              # -> skins/
    python3 tools/make_tui.py --preview    # also build/tui-preview/<page>.png: the background plus every widget at sample values
"""
import hashlib, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "skins")
PREVIEW = os.path.join(ROOT, "build", "tui-preview")
GEN = open(os.path.join(ROOT, "src", "params_gen.h")).read()
KEYS = re.findall(r'^\s*\{"([^"]+)"', GEN, re.M)   # VST order (generated)
UI_STEPS = int(re.search(r'\{"ui_open", "[^"]*", 0\.0f, (\d+)\.0f', GEN).group(1)) + 1
OPTIONS = {p["key"]: p.get("options") for p in json.load(open(os.path.join(ROOT, "vst", "params.json")))["params"]}
FONT = "Titillium Web"
GESTURE = "Instant"


def P(key):
    return "Parameter %d" % KEYS.index(key)


# ---- a JSON writer that keeps key order and allows the overlay widgets' duplicate "version" key ------------------------
class Obj:
    def __init__(self, *pairs):
        self.pairs = list(pairs)


def dump(v, ind=0):
    sp = "  " * ind
    pairs = v.pairs if hasattr(v, "pairs") else list(v.items()) if isinstance(v, dict) else None
    if pairs is not None:
        if not pairs:
            return "{}"
        return "{\n%s\n%s}" % (",\n".join("%s  %s: %s" % (sp, dump(k), dump(x, ind + 1)) for k, x in pairs), sp)
    if isinstance(v, list):
        return "[]" if not v else "[\n%s\n%s]" % (",\n".join(sp + "  " + dump(x, ind + 1) for x in v), sp)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v) if isinstance(v, float) else str(v)
    return '"%s"' % str(v).replace("\\", "\\\\").replace('"', '\\"')


# ---- building blocks -----------------------------------------------------------------------------------------------------
def B(x, y, w, h):
    return "%d %d %d %d" % (round(x), round(y), round(w), round(h))


def bounds(b, focus="No", visible="Always", ind=None):
    d = {"version": 2 if ind else 1, "acceptsHWFocus": focus, "showWhenDataModelInvalid": "Show", "whenVisible": visible,
         "boundsType": "Absolute", "bounds": b}
    if ind:
        d["additionalInvalidatingHandles"] = ind
    return d


def entry(name, typ, data, b, remap=None, focus="No", visible="Always", ind=None):
    return {"version": 2, "componentData": {"version": 1, "name": name, "type": typ, "data": data},
            "handle remapping": {"version": 1, "map": [{"key": "Data", "value": remap}] if remap else []},
            "bounds": bounds(b, focus, visible, ind)}


def bg(colour="0", image=""):
    return {"version": 1, "focussed": {"version": 1, "colour": colour, "image": image},
            "unfocussed": {"version": 1, "colour": colour, "image": image}}


def component(children, actions=None, ignore=False, background=None):
    return {"version": 2, "actions": actions or [], "backgroundData": background or bg(), "ignoreMousePresses": ignore,
            "disableCoarseDataWheel": False, "componentsData": children}


def act(on, handler, extra=""):
    return {"version": 1, "onAction": on, "handler": handler, "handleName": "Data", "additionalData": extra}


FOCUS = {"version": 1, "backgroundColour": "14ffffff", "outlineColour": "ffff9a1f", "backgroundInset": 2.0, "outlineThickness": 1.5}


def text_style(h=24.0, colour="fff2f2f4", style="SemiBold", just="horizontallyCentred verticallyCentred", case="Original"):
    return {"version": 1, "font": {"version": 1, "name": FONT, "style": style, "height": h}, "colour": colour,
            "justification": just, "case": case}


def label(b, remap, **ts):
    return entry("label", "Label", {"version": 1, "textStyle": text_style(**ts), "type": "Value", "handleName": "Data"}, b, remap)


def button(name, remap, on, off, b, button_id=1, group=1, focus="No", ind=None):
    return entry(name, "Button", {"version": 2, "onImage": on, "offImage": off, "buttonId": button_id, "numButtonsInGroup": group,
                                  "handleName": "Data", "gestureBehaviour": GESTURE}, b, remap=remap, focus=focus, ind=ind)


# ---- art assets -----------------------------------------------------------------------------------------------------------
_made = set()


def asset(name, make):
    if name not in _made:
        make().save(os.path.join(OUT, name))
        _made.add(name)
    return name


def knob_strip(bip):
    from PIL import Image
    import make_profit_skin as art
    def make():
        D, n = 78, 128
        strip = Image.new("RGBA", (D, D * n), (0, 0, 0, 0))
        for i in range(n):
            f = Image.new("RGBA", (D, D), (0, 0, 0, 0))
            art.knob(f, D / 2, D / 2, i / (n - 1), bipolar=bip)
            strip.alpha_composite(f, (0, i * D))
        return strip
    return asset("knob_%s.png" % ("bi" if bip else "uni"), make)


def led_img(on):
    from PIL import Image
    import make_profit_skin as art
    def make():
        im = Image.new("RGBA", (64, 56), (0, 0, 0, 0))
        art.led(im, 32, 28, on)
        return im
    return asset("led_%s.png" % ("on" if on else "off"), make)


def clear_img(w, h, alpha=0):
    from PIL import Image
    return asset("clear_%dx%d_%d.png" % (w, h, alpha), lambda: Image.new("RGBA", (w, h), (255, 255, 255, alpha)))


def key_img(w, h, caption, lit):
    from PIL import Image
    import make_profit_skin as art
    slug = re.sub(r"[^A-Za-z0-9]", "_", caption.replace("+", "p").replace("-", "m").replace("<", "lt").replace(">", "gt"))
    def make():
        im = Image.new("RGBA", (w + 12, h + 14), (0, 0, 0, 0))
        art.key(im, (w + 12) / 2, (h + 14) / 2 - 1, w, h, caption, lit=lit)
        return im
    return asset("key_%dx%d_%s_%s.png" % (w, h, slug, "on" if lit else "off"), make)


def tile_img(w, h, lit):
    from PIL import Image, ImageDraw
    import make_profit_skin as art
    def make():
        im = Image.new("RGBA", (w + 1, h + 1), (0, 0, 0, 0))
        if lit:   # translucent: the name Label underneath shows through (a Label on top of a Button swallows taps)
            ImageDraw.Draw(im).rounded_rectangle([0, 0, w, h], 4, fill=(255, 154, 31, 46), outline=art.AMBER + (255,), width=2)
        return im
    return asset("tile_%dx%d_%s.png" % (w, h, "on" if lit else "off"), make)


def opt_img(w, h, text, lit):
    from PIL import Image, ImageDraw
    import make_profit_skin as art
    slug = hashlib.md5(text.encode()).hexdigest()[:8]
    def make():
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, w - 1, h - 1], 5, fill=art.AMBER if lit else (34, 9, 7), outline=art.LINE if not lit else art.AMBER)
        px = 18
        while px > 11 and d.textlength(text, font=art.font(px)) > w - 14:
            px -= 1
        d.text((w / 2, h / 2), text, font=art.font(px), fill=(20, 12, 4) if lit else art.AMBER, anchor="mm")
        return im
    return asset("opt_%dx%d_%s_%s.png" % (w, h, slug, "on" if lit else "off"), make)


# ---- reusable components --------------------------------------------------------------------------------------------------
DEFS = {}


def knob_def(bip):
    name = "pknob_bi" if bip else "pknob"
    if name not in DEFS:
        strip = knob_strip(bip)
        DEFS[name] = component([
            entry("focus", "Focus", FOCUS, "-4 -4 86 86", visible="WhenFocussed"),
            entry("strip", "Knob", {"version": 3, "knobType": "FilmStrip", "filmStrip": strip, "numFrames": 128, "invert": False,
                                    "dragOrientation": "Vertical", "handleName": "Data"}, "0 0 78 78"),
        ], actions=[act("Mouse Down", "Q-Link"), act("Double Click", "Show Overlay", "knob overlay"),
                    act("Enter Pressed", "Show Overlay", "knob overlay")])
    return name


def field_def(w, h):
    """A display's value (program, bank ...): an invisible value slider over the display text (data wheel, Q-Link, drag)."""
    name = "field%dx%d" % (w, h)
    if name not in DEFS:
        ts = text_style(20.0, colour="00000000")
        DEFS[name] = component([
            entry("focus", "Focus", {"version": 1, "backgroundColour": "14ff4a35", "outlineColour": "ffff4a35",
                                     "backgroundInset": 0.0, "outlineThickness": 1.5}, "0 0 %d %d" % (w, h), visible="WhenFocussed"),
            entry("field", "Knob", {"version": 4, "knobType": "ValueSlider", "textStyle": ts, "dragOrientation": "Horizontal",
                                    "handleName": "Data"}, "0 0 %d %d" % (w, h)),
        ], actions=[act("Mouse Down", "Q-Link")])
    return name


def overlay_def():
    return component([entry("overlay", "KnobOverlay", Obj(
        ("version", 2), ("version", 1),
        ("actions", [{"version": 1, "onAction": "Focus Lost", "handler": "Focus Lost", "handleName": "Focus Lost", "additionalData": ""}]),
        ("overlayType", "Knob With Header"), ("scaleType", "Linear"), ("polarityType", "Unipolar"),
        ("showMinusSign", True), ("handleName", "Data")), "0 0 1280 800", focus="Yes")], ignore=True)


PICK_N = {}      # enum key -> its ui_open number (k + 1)


def pick_def(opts):
    """A drawn pick-list for one option list: a panel, one radio Button per option (text baked in), a close key on ui_open."""
    from PIL import Image, ImageDraw
    import make_profit_skin as art
    n = len(opts)
    cols = 1 if n <= 8 else 2 if n <= 16 else 4 if n <= 24 else 5
    rows = (n + cols - 1) // cols
    cw, ch, gap, hdr = (220 if cols <= 2 else 226), 44, 4, 46
    pw, ph = cols * (cw + gap) + gap + 12, hdr + rows * (ch + gap) + gap + 10
    name = "list_%d_%s" % (n, hashlib.md5("|".join(opts).encode()).hexdigest()[:8])
    if name not in DEFS:
        def panel():
            im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([0, 0, pw - 1, ph - 1], 10, fill=(20, 20, 23, 250), outline=art.AMBER, width=2)
            d.text((16, hdr / 2 + 1), "S E L E C T", font=art.font(14, "Bold"), fill=art.INK, anchor="lm")
            return im
        kids = [entry("panel", "Image", {"version": 2, "imageType": "Regular", "colour": "0", "image": asset(name + "_bg.png", panel)},
                      "0 0 %d %d" % (pw, ph))]
        for i, o in enumerate(opts):
            r, c = i % rows, i // rows          # fill down the columns
            kids.append(button("opt %d" % i, None, opt_img(cw, ch, o, True), opt_img(cw, ch, o, False),
                               B(6 + gap + c * (cw + gap), hdr + gap + r * (ch + gap), cw, ch), button_id=i, group=n))
        kids.append(button("close", P("ui_open"), key_img(52, 32, "X", True), key_img(52, 32, "X", False),
                           B(pw - 70, 4, 64, 46), button_id=0, group=UI_STEPS))
        DEFS[name] = component(kids)
    return name, pw, ph


# ---- pages -> widgets -----------------------------------------------------------------------------------------------------
class Built:
    def __init__(self, page):
        self.page, self.kids, self.lists, self.sample = page, [], [], {}

    def knob(self, key, cx, cy, sample):
        bip = sample[2]
        comp = knob_def(bip)
        self.kids.append(entry(key, comp, {"version": 1, "handleName": "Data"}, B(cx - 39, cy - 39, 78, 78), remap=P(key), focus="Yes"))
        self.sample[key] = sample

    def value(self, key, cx, cy, w=124, h=24.0, **ts):
        self.kids.append(label(B(cx - w / 2, cy - 13, w, 26), P(key), h=h, **ts))

    def led(self, key, cx, cy, on):
        self.kids.append(button(key, P(key), led_img(True), led_img(False), B(cx - 32, cy - 28, 64, 56)))
        self.sample[key] = on

    def pick(self, key, cx, cy, w, h, mock):
        opts = OPTIONS[key]
        if key not in PICK_N:
            PICK_N[key] = len(PICK_N) + 1
            assert PICK_N[key] < UI_STEPS, "too many pick-lists for ui_open"
        n = PICK_N[key]
        x0, y0 = cx - w / 2, cy - h / 2
        self.kids.append(label(B(x0 + 4, y0, w - 30, h), P(key), h=24.0, colour="ffff9a1f"))
        self.kids.append(button(key + " field", P("ui_open"), clear_img(int(w), int(h), 40), clear_img(int(w), int(h)),
                                B(x0, y0, w, h), button_id=n, group=UI_STEPS))
        comp, pw, ph = pick_def(opts)
        if pw < 400:   # a short list opens under its field (or above it near the bottom)
            x = max(8, min(cx - pw / 2, 1272 - pw))
            y = y0 + h + 4 if y0 + h + 4 + ph <= 620 else y0 - 4 - ph
            y = max(4, y)
        else:
            x, y = (1280 - pw) / 2, max(4, (628 - ph) / 2)
        self.lists.append(entry("list " + key, comp, {"version": 1, "handleName": "Data"}, B(x, y, pw, ph), remap=P(key),
                                ind=["IndexedEnabling/%d/%d/%s" % (n, UI_STEPS, P("ui_open"))]))
        self.sample[key] = mock

    def momentary(self, key, cx, cy, w, h, caption):
        self.kids.append(button(key, P(key), key_img(w, h, caption, True), key_img(w, h, caption, False),
                                B(cx - (w + 12) / 2, cy - (h + 14) / 2 + 1, w + 12, h + 14)))

    def hit(self, key, x, y, w, h):
        self.kids.append(button(key, P(key), clear_img(w, h, 50), clear_img(w, h), B(x, y, w, h)))


def build(page):
    import skin_pages as sp
    b = Built(page)
    for p in page.panels:
        for c, cx, top, pitch in p.cells:
            kind, key, cap, mock = c
            if kind == "knob":
                b.knob(key, cx, top + 66, mock)
                b.value(key, cx, top + 132, w=130, h=28.0)
                b.sample[key + "$"] = mock[1]
            elif kind == "led":
                b.led(key, cx, top + 66, mock)
            elif kind == "pick":
                b.pick(key, cx, top + 88, sp.pick_w(pitch), 46, mock)
    for it in page.items:
        if isinstance(it, sp.LCD):
            ax = 52 if it.prev else 8
            ix, iw = it.x + ax, it.w - 2 * ax
            just = "left verticallyCentred" if it.align == "lm" else "horizontallyCentred verticallyCentred"
            b.kids.append(label(B(ix + (14 if it.align == "lm" else 0), it.y + 6, iw - (14 if it.align == "lm" else 0), it.h - 12),
                                P(it.text), h=27.0, colour="ffff4a35", just=just))
            b.sample[it.text + "$"] = it.mock
            if it.field:
                b.kids.append(entry(it.field + " field", field_def(iw, it.h), {"version": 1, "handleName": "Data"}, B(ix, it.y, iw, it.h),
                                    remap=P(it.field), focus="Yes"))
            if it.prev:
                b.hit(it.prev, it.x, it.y, ax, it.h)
                b.hit(it.nxt, it.x + it.w - ax, it.y, ax, it.h)
        elif isinstance(it, sp.KEYW):
            b.momentary(it.key, it.cx, it.cy, it.w, it.h, it.caption)
        elif isinstance(it, sp.PAGETXT):
            b.value(it.key, it.cx, it.cy, w=it.w + 30, h=22.0)
            b.sample[it.key + "$"] = it.mock
        elif isinstance(it, sp.TILES):
            for i in range(it.n):
                c, r = divmod(i, it.rows)
                x, y = it.x0 + c * it.pitch_x, it.y0 + r * it.pitch_y
                key = "%s%d" % (it.prefix, i + 1)
                b.kids.append(label(B(x + 12, y, it.tw - 16, it.th), P(key), h=24.0, colour="ffd9d9de", just="left verticallyCentred"))
                b.kids.append(button(key, P(key), tile_img(it.tw, it.th, True), tile_img(it.tw, it.th, False), B(x, y, it.tw + 1, it.th + 1)))
                b.sample[key + "$"] = it.mock[i] if i < len(it.mock) else ""
                b.sample[key] = i == 0
    return b


def tabs_for(page, b, bgname):
    out, qmaps = [], []
    for si, (subname, idxs) in enumerate(page.sub_list()):
        groups, qrows = [], []
        for pi in idxs:
            p = page.panels[pi]
            r = p.qrect()
            if r and p.qkeys():
                groups.append(B(r[0], r[1], r[2] - r[0], r[3] - r[1]))
                qrows.append(p.qkeys())
        assert len(qrows) <= 4, "%s: more than four Q-Link groups" % subname
        kids = [entry("bg", "Image", {"version": 2, "imageType": "Regular", "colour": "0", "image": bgname}, "0 0 1280 628")] + b.kids + b.lists
        sub = page.first_sub + si if page.subs else 0
        out.append({"version": 1, "tabName": subname if page.subs else page.tab, "fnKeyIndex": page.fn, "fnKeySubIndex": sub,
                    "componentDefinition": component(kids, background=bg("ff131315")), "qlinkBoundsData": groups})
        q = {"Q-Link %d" % n: -1 for n in range(1, 17)}
        for gi, keys in enumerate(qrows):
            for i, key in enumerate(keys[:4]):
                q["Q-Link %d" % (13 - 4 * gi + i)] = KEYS.index(key)
        qmaps.append({"Tab": page.fn + 1, "SubTab": sub + 1, "Bank Direction": "RowTopDown", "Q-Links": q})
    return out, qmaps


# ---- preview: the background plus the widgets at sample values (checks that the live parts land on the art) --------------
def render_preview(b, bgname):
    from PIL import Image, ImageDraw
    import make_profit_skin as art
    img = Image.open(os.path.join(OUT, bgname)).convert("RGBA")
    d = ImageDraw.Draw(img)
    for k in b.kids:
        cd, (x, y, w, h) = k["componentData"], [int(v) for v in k["bounds"]["bounds"].split()]
        typ, data = cd["type"], cd["data"]
        remap = k["handle remapping"]["map"][0]["value"] if k["handle remapping"]["map"] else None
        key = KEYS[int(remap.split()[-1])] if remap else None
        if typ in DEFS and typ.startswith("pknob"):
            frac = b.sample.get(key, (0.5,))[0]
            strip = Image.open(os.path.join(OUT, knob_strip(typ.endswith("bi"))))
            f = int(round(frac * 127))
            img.alpha_composite(strip.crop((0, f * 78, 78, f * 78 + 78)), (x, y))
        elif typ == "Button" and key != "ui_open":
            lit = bool(b.sample.get(key)) and data["numButtonsInGroup"] == 1
            pic = Image.open(os.path.join(OUT, data["onImage" if lit else "offImage"])).convert("RGBA")
            img.alpha_composite(pic, (x + (w - pic.width) // 2, y + (h - pic.height) // 2))
        elif typ == "Label":
            ts = data["textStyle"]
            txt = b.sample.get(key + "$", b.sample.get(key) if isinstance(b.sample.get(key), str) else "")
            col = ts["colour"]
            rgb = tuple(int(col[i:i + 2], 16) for i in (2, 4, 6))
            fnt = art.font(int(ts["font"]["height"] * 0.66))
            left = "left" in ts["justification"]
            d.text((x if left else x + w / 2, y + h / 2), txt or "", font=fnt, fill=rgb, anchor="lm" if left else "mm")
    return img


def main():
    preview = "--preview" in sys.argv
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import skin_pages
    pages = skin_pages.all_pages()
    tabs, qmaps, repl, seen = [], [], [], set()
    if preview:
        os.makedirs(PREVIEW, exist_ok=True)
    for page in pages:
        bgname = "bg_%s.png" % page.name
        page.render(live=False).convert("RGB").save(os.path.join(OUT, bgname))
        b = build(page)
        t, q = tabs_for(page, b, bgname)
        tabs += t
        qmaps += q
        for p in page.panels:
            for c, _, _, _ in p.cells:
                key = c[1]
                if OPTIONS.get(key) and key not in seen:
                    seen.add(key)
                    repl.append({"key": P(key), "value": OPTIONS[key]})
        if preview:
            render_preview(b, bgname).convert("RGB").save(os.path.join(PREVIEW, page.name + ".png"))
    defs = [{"key": "knob overlay", "value": overlay_def()}] + [{"key": k, "value": v} for k, v in DEFS.items()]
    tui = {"pageData": {"version": 1,
                        "componentDefinitions": {"version": 2, "importFiles": [], "localComponentDefinitions": defs},
                        "replacementStrings": repl, "info": {"version": 1, "type": "CompleteDescription"}, "tabs": tabs}}
    text = dump(tui) + "\n"
    assert "object at 0x" not in text, "a Python object leaked into TUI.json"
    open(os.path.join(OUT, "TUI.json"), "w").write(text)
    ql = {"version": 4, "info": {"version": 1, "type": "CompleteDescription"},
          "Screen Mode Q-Links": {"version": 4, "map": qmaps}, "Program Mode Q-Links": {"Q-Link %d" % n: -1 for n in range(1, 17)}}
    open(os.path.join(OUT, "Q-Links.json"), "w").write(dump(ql) + "\n")
    print("wrote %s - %d tabs, %d pick-lists, %d files" % (OUT, len(tabs), len(PICK_N), len(os.listdir(OUT))))


if __name__ == "__main__":
    # Run inside the importable module, not __main__ (a module imported twice keeps two registries).
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import make_tui
    make_tui.main()
