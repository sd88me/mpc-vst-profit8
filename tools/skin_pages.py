#!/usr/bin/env python3
"""Profit-08 2 skin pages. Each page's coordinates are defined once, here, as panels (one printed section = one Q-Link group of up to
four controls) and a few free items (displays, keys, tiles, the wordmark). The same definitions draw
  * the design mock-ups (docs/skin-preview/*.png, sample values baked in):   python3 tools/skin_pages.py [--overlay]
  * the real skin (tools/make_tui.py): the static art goes into one background PNG per page, the live parts become TUI widgets at the
    same coordinates (film-strip knobs, LED buttons, drawn pick-lists, value labels, display text, keys, list tiles).

Tabs (one key each, the released order): PROGRAM, BANKS, OSC FILTER, AMP LFO, MODS, SEQ. The MPC has 16 Q-Links (four groups) per tab or
sub-tab, so a page with more than four groups gets sub-tabs with the same art: OSC FILTER (OSC / FILTER), AMP LFO (AMP / LFO),
MODS (MODS / CTRL), SEQ (SEQ 1 .. SEQ 4; two sequences per page art).
Content area 1280 x 628 (the MPC's tab area starts 110 px down the screen).
"""
import os, random, re, sys
from PIL import Image, ImageDraw

import make_profit_skin as art

ROOT = art.ROOT
PREVIEW = os.path.join(ROOT, "docs", "skin-preview")
ROW_H = 146
BIPOLAR = set(re.findall(r'\{"(\w+)", \d+, \d+, \d+, "(?:bi|cents)"\}', open(os.path.join(ROOT, "src", "patch_tab.h")).read()))


# ---- controls: (kind, key, caption, mock) ----------------------------------------------------------------------------
def K(key, cap, frac=0.5, text=""): return ("knob", key, cap, (frac, text, key in BIPOLAR))
def LED(key, cap, on=False): return ("led", key, cap, on)
def PK(key, cap, text): return ("pick", key, cap, text)


class Panel:
    def __init__(self, x, y, w, h, title, ctrls, ql=4):
        self.x, self.y, self.w, self.h, self.title, self.ctrls = x, y, w, h, title, ctrls
        self.ql = min(ql, len(ctrls))     # the first ql controls form the Q-Link group
        self.extra_q = []                 # Q-Link keys that are not drawn controls of this panel (e.g. the displays' values)
        cols = max(len(ctrls), 1)
        pitch = (w - 16) / cols
        off = (h - ROW_H) / 2
        self.cells = [(c, x + 8 + pitch * (i + 0.5), y + off, pitch) for i, c in enumerate(ctrls)]

    def qkeys(self):
        return [c[0][1] for c in self.cells[:self.ql]] + self.extra_q

    def qrect(self):
        if self.extra_q and not self.ql:
            return (self.x + 6, self.y + 30, self.x + self.w - 6, self.y + self.h - 6)
        if not self.ql:
            return None
        cs = self.cells[:self.ql]
        p = cs[0][3]
        return (cs[0][1] - p / 2 + 2, self.y + 30, cs[-1][1] + p / 2 - 2, self.y + self.h - 6)


# ---- free items ---------------------------------------------------------------------------------------------------------
class LCD:      # a display with step arrows: text = a text param's value; prev / next = momentary keys; field = the value it steps
    def __init__(self, x, y, w, h, text, mock, prev=None, nxt=None, field=None, caption=None, align="mm"):
        self.__dict__.update(locals()); del self.__dict__["self"]


class KEYW:     # a momentary key with its caption baked in
    def __init__(self, key, cx, cy, w, h, caption):
        self.__dict__.update(locals()); del self.__dict__["self"]


class PAGETXT:  # plain live text (the BANKS page number)
    def __init__(self, key, cx, cy, w, mock):
        self.__dict__.update(locals()); del self.__dict__["self"]


class TILES:    # the BANKS lists: tiles with the engine's names, lit = current
    def __init__(self, prefix, n, cols, rows, x0, y0, tw, th, pitch_x, pitch_y, mock):
        self.__dict__.update(locals()); del self.__dict__["self"]


class WORDMARK:
    def __init__(self, x, y, w, h):
        self.__dict__.update(locals()); del self.__dict__["self"]


class Page:
    def __init__(self, name, tab, fn, subs=None):
        """subs: [(sub-tab label, [panel indices that carry the Q-Links])]; None = one tab, every Q-Link panel."""
        self.name, self.tab, self.fn, self.subs = name, tab, fn, subs
        self.first_sub = 0
        self.panels, self.items = [], []

    def add(self, *a, **k):
        p = Panel(*a, **k)
        self.panels.append(p)
        return p

    def sub_list(self):
        return self.subs or [(self.tab, list(range(len(self.panels))))]

    # ---- the mock-up / the background art ----
    def render(self, overlay=False, live=True):
        """live=True: the mock-up (sample values); live=False: only the static art (the TUI background)."""
        img = art.plate()
        for p in self.panels:
            art.frame(img, p.x, p.y, p.w, p.h, p.title)
            for c, cx, top, pitch in p.cells:
                draw_ctrl(img, c, cx, top, pitch, live)
        for it in self.items:
            draw_item(img, it, live)
        if overlay:
            for p in self.panels:
                if p.qrect():
                    art.qlink_overlay(img, p.qrect())
        return img


def pick_w(pitch):
    return min(126, int(pitch) - 10)


def draw_ctrl(img, c, cx, top, pitch, live):
    kind, key, cap, mock = c
    d = ImageDraw.Draw(img)
    if kind == "knob":
        frac, text, bip = mock
        if live:
            art.knob(img, cx, top + 66, frac, bipolar=bip)
            art.caption(d, cx, top + 132, text, size=20, col=art.INK)
        art.caption(d, cx, top + 111, cap, size=14)
    elif kind == "led":
        if live:
            art.led(img, cx, top + 66, mock)
        art.caption(d, cx, top + 111, cap, size=14)
    elif kind == "pick":
        art.caption(d, cx, top + 46, cap.upper().replace(" ", "  "), size=13, weight="Bold")
        art.pick(img, cx, top + 88, pick_w(pitch), 46, mock if live else "")


def draw_item(img, it, live):
    d = ImageDraw.Draw(img)
    if isinstance(it, LCD):
        if it.caption:
            d.text((it.x + 4, it.y - 14), it.caption, font=art.font(13, "Bold"), fill=art.INK, anchor="lm")
        art.lcd(img, it.x, it.y, it.w, it.h, it.mock if live else "", arrows=bool(it.prev), align=it.align)
    elif isinstance(it, KEYW):
        if live:
            art.key(img, it.cx, it.cy, it.w, it.h, it.caption)
    elif isinstance(it, PAGETXT):
        if live:
            d.text((it.cx, it.cy), it.mock, font=art.font(16), fill=art.INK, anchor="mm")
    elif isinstance(it, TILES):
        for i in range(it.n):
            c, r = divmod(i, it.rows)
            x, y = it.x0 + c * it.pitch_x, it.y0 + r * it.pitch_y
            lit = live and i == 0
            d.rounded_rectangle([x, y, x + it.tw, y + it.th], 4, fill=(60, 30, 6) if lit else (22, 22, 25),
                                outline=art.AMBER if lit else (74, 74, 80))
            if live and i < len(it.mock) and it.mock[i]:
                d.text((x + 12, y + it.th / 2), it.mock[i], font=art.font(16), fill=art.AMBER if lit else art.INK_DIM, anchor="lm")
    elif isinstance(it, WORDMARK):
        art.wordmark(img, it.x, it.y, it.w, it.h)


def rows(page, spec, y0=10, gap=8, h=ROW_H):
    """spec: list of rows; each row a list of (w, title, ctrls[, ql]) laid left to right from x=20 with 16 px gaps."""
    y = y0
    for row in spec:
        x = 20
        for item in row:
            w, title, ctrls = item[:3]
            ql = item[3] if len(item) > 3 else 4
            if ctrls is not None:
                page.add(x, y, w, h, title, ctrls, ql=ql)
            x += w + 16
        y += h + gap


# ---- pages -------------------------------------------------------------------------------------------------------------
def program():
    pg = Page("program", "PROGRAM", 0)
    pg.add(20, 10, 1240, 146, "Program", [], ql=0)   # the displays: arrows, touch, data wheel (four Q-Link groups below)
    pg.items += [LCD(46, 78, 566, 56, "patch_name", "001 P5 Brass", "program_prev", "program_next", "program", "PROGRAM"),
                 LCD(666, 78, 568, 56, "bank_name", "Factory Bank 1", "bank_prev", "bank_next", "bank", "BANK")]
    rows(pg, [
        [(612, "Keyboard", [PK("layer", "Edit Layer", "A"), PK("kbd_mode", "Keyboard", "Normal"), K("split_point", "Split Point", .5, "C3"),
                            LED("unison", "Unison")]),
         (612, "Voice", [PK("unison_mode", "Unison Mode", "1 Voice"), PK("key_mode", "Unison Assign", "Low"),
                         K("voice_vol", "Voice Volume", 1.0, "127"), K("bend_range", "Bend Range", .33, "4")])],
        [(612, "Arpeggiator / Sequencer", [LED("arp", "Arpeggiator"), PK("arp_mode", "Arp Mode", "Up"), LED("gseq", "Gated Seq"),
                                            PK("seq_trig", "Seq Trigger", "Normal")]),
         (612, "Clock", [K("tempo", "BPM", .4, "120 BPM"), PK("clock_div", "Clock Divide", "Eighth"), PK("clock_src", "Clock", "Host"),
                         PK("seq_run", "Seq Run", "Stop")])],
        [(612, "System", [PK("quality", "Quality", "Eco 1x")], 0)],
    ], y0=164)
    sysp = pg.panels[-1]
    sysp.cells = [(sysp.cells[0][0], 20 + 92, sysp.y, 140)]
    pg.items += [LCD(200, 554, 410, 52, "status", "6 banks", align="lm"), WORDMARK(790, 482, 400, 138)]
    return pg


def banks():
    pg = Page("banks", "BANKS", 1)
    bp = pg.add(20, 76, 300, 544, "Banks", [], ql=0)
    bp.extra_q = ["browse_bank_index", "program", "patch_page_index"]
    pg.add(332, 76, 928, 544, "Programs", [], ql=0)
    rnd = random.Random(5)
    words = ["Brass", "Pad", "Sync Lead", "Strings", "Bass", "Sweep", "Bell", "Poly", "Choir", "Pluck", "Organ", "Wind"]
    pg.items += [
        LCD(36, 10, 290, 50, "browse_bank_name", "1 Factory Bank 1", "prev_browse_bank", "next_browse_bank", "browse_bank_index"),
        LCD(340, 10, 540, 50, "patch_name", "001 P5 Brass", "program_prev", "program_next", "program"),
        KEYW("patch_page_prev", 920, 35, 44, 40, "<"), PAGETXT("patch_page_text", 978, 35, 56, "PAGE 1/3"),
        KEYW("patch_page_next", 1036, 35, 44, 40, ">"),
        KEYW("fav_add", 1124, 35, 72, 40, "+ FAV"), KEYW("fav_del", 1206, 35, 72, 40, "- FAV"),
        TILES("bank_slot_", 11, 1, 11, 36, 128, 268, 37, 0, 43,
              ["1 Factory Bank 1", "2 Factory Bank 2", "3 Factory Bank 3", "4 Factory Bank 4", "5 Factory Bank 5", "6 User Sounds"]),
        TILES("patch_slot_", 45, 3, 15, 348, 128, 293, 28, 299, 32,
              ["%03d %s %d" % (i + 1, words[rnd.randrange(len(words))], rnd.randint(1, 9)) for i in range(45)]),
    ]
    return pg


def osc_filter():
    pg = Page("osc_filter", "OSC FILTER", 2, subs=[("OSC", [0, 1, 2, 3]), ("FILTER", [4, 5, 6])])
    osc = lambda n, f: [K("osc%d_freq" % n, "Frequency", f, "C2"), K("osc%d_fine" % n, "Fine", .5, "0"),
                        K("osc%d_shape" % n, "Shape / PW", .3, "Saw"), K("osc%d_glide" % n, "Glide", 0, "0")]
    rows(pg, [
        [(612, "Oscillator 1", osc(1, .35)), (612, "Oscillator 2", osc(2, .36))],
        [(612, "Mix", [K("osc_mix", "Osc Mix 1-2", .5, "64"), K("noise", "Noise", 0, "0"), K("slop", "Osc Slop", .1, "5"),
                       LED("sync", "Sync 2>1")]),
         (612, "Keyboard / Glide", [LED("osc1_key", "Osc 1 Keybd", True), LED("osc2_key", "Osc 2 Keybd", True),
                                    PK("glide_mode", "Glide Mode", "Fixed Rate")])],
        [(612, "Low Pass Filter", [LED("poles", "4 Pole", True), K("lpf_freq", "Frequency", .6, "102"), K("lpf_res", "Resonance", .2, "25"),
                                   K("lpf_key", "Key Amount", .5, "64")]),
         (612, "Filter Modulation", [K("lpf_audmod", "Audio Mod", 0, "0"), K("fenv_amt", "Env Amount", .7, "+60"),
                                     K("fenv_vel", "Velocity", .3, "40"), K("fenv_delay", "Env Delay", 0, "0")])],
        [(612, "Filter Envelope", [K("fenv_a", "Attack", .05, "5"), K("fenv_d", "Decay", .45, "58"), K("fenv_s", "Sustain", .3, "40"),
                                   K("fenv_r", "Release", .35, "45")]),
         (612, None, None)],
    ])
    pg.items.append(WORDMARK(760, 476, 400, 138))
    return pg


def amp_lfo():
    pg = Page("amp_lfo", "AMP LFO", 3, subs=[("AMP", [0, 1, 2, 3]), ("LFO", [4, 5, 6, 7])])
    adsr = lambda p, v: [K(p + "_a", "Attack", v[0], str(int(v[0] * 127))), K(p + "_d", "Decay", v[1], str(int(v[1] * 127))),
                         K(p + "_s", "Sustain", v[2], str(int(v[2] * 127))), K(p + "_r", "Release", v[3], str(int(v[3] * 127)))]
    lfo = lambda n, sh, de, on: [K("lfo%d_freq" % n, "Frequency", .4, "3.2 Hz"), PK("lfo%d_shape" % n, "Shape", sh),
                                 K("lfo%d_amt" % n, "Amount", .2, "25"), PK("lfo%d_dest" % n, "Destination", de), LED("lfo%d_sync" % n, "Sync", on)]
    rows(pg, [
        [(612, "Amp Envelope", adsr("aenv", (.0, .4, .8, .3))),
         (612, "Amp", [K("vca_level", "VCA Level", 0, "0"), K("vca_env", "Env Amount", 1, "127"), K("vca_vel", "Velocity", .5, "64"),
                       K("aenv_delay", "Env Delay", 0, "0"), K("spread", "Pan Spread", 0, "0")])],
        [(612, "Envelope 3", [PK("env3_dest", "Destination", "Osc1 Freq"), K("env3_amt", "Amount", .5, "0"),
                              K("env3_vel", "Velocity", 0, "0"), K("env3_delay", "Delay", 0, "0"), LED("env3_repeat", "Repeat")]),
         (612, "Envelope 3  ·  Stages", adsr("env3", (.1, .3, 0, .2)))],
        [(612, "LFO 1", lfo(1, "Triangle", "Filter", False)), (612, "LFO 2", lfo(2, "Saw", "Osc1 Freq", False))],
        [(612, "LFO 3", lfo(3, "Square", "Off", True)), (612, "LFO 4", lfo(4, "Random", "Off", False))],
    ])
    return pg


def mods():
    pg = Page("mods", "MODS", 4, subs=[("MODS", [0, 1, 3, 4]), ("CTRL", [2, 5, 6, 7])])
    mod = lambda n, s, de, f: [PK("mod%d_src" % n, "Source", s), PK("mod%d_dest" % n, "Destination", de), K("mod%d_amt" % n, "Amount", f, "+20")]
    ctl = lambda a, cap, de, f: [K(a + "_amt", cap + " Amt", f, "+30"), PK(a + "_dest", cap + " Dest", de)]
    rows(pg, [
        [(404, "Modulator 1", mod(1, "LFO 1", "Filter", .6)), (404, "Modulator 2", mod(2, "Off", "Off", .5)),
         (400, "Wheel / Pressure", ctl("wheel", "Wheel", "LFO Amt", .7) + ctl("press", "Press", "Off", .5))],
        [(404, "Modulator 3", mod(3, "Off", "Off", .5)), (404, "Modulator 4", mod(4, "Off", "Off", .5)),
         (400, "Breath / Velocity", ctl("breath", "Breath", "Off", .5) + ctl("vel", "Velocity", "Off", .5))],
        [(824, "Sequence Destinations", [PK("seq%d_dest" % n, "Seq %d" % n, d) for n, d in ((1, "Osc Freq"), (2, "Off"), (3, "Off"), (4, "Off"))]),
         (400, "Foot Controller", ctl("foot", "Foot", "Off", .5), 2)],
    ], h=196)
    return pg


def seq(a, b, first_sub):
    pg = Page("seq_%d_%d" % (a, b), "SEQ", 5, subs=[("SEQ %d" % a, [0, 1, 2, 3]), ("SEQ %d" % b, [4, 5, 6, 7])])
    pg.first_sub = first_sub
    rnd = random.Random(a)
    blk = lambda s, n0: [K("s%d_%d" % (s, n), str(n), v / 126, str(v)) for n in range(n0, n0 + 4) for v in [rnd.randint(0, 126)]]
    rows(pg, [
        [(612, "Sequence %d  ·  Steps 1-4" % a, blk(a, 1)), (612, "Sequence %d  ·  Steps 5-8" % a, blk(a, 5))],
        [(612, "Sequence %d  ·  Steps 9-12" % a, blk(a, 9)), (612, "Sequence %d  ·  Steps 13-16" % a, blk(a, 13))],
        [(612, "Sequence %d  ·  Steps 1-4" % b, blk(b, 1)), (612, "Sequence %d  ·  Steps 5-8" % b, blk(b, 5))],
        [(612, "Sequence %d  ·  Steps 9-12" % b, blk(b, 9)), (612, "Sequence %d  ·  Steps 13-16" % b, blk(b, 13))],
    ])
    return pg


def all_pages():
    return [program(), banks(), osc_filter(), amp_lfo(), mods(), seq(1, 2, 0), seq(3, 4, 2)]


if __name__ == "__main__":
    overlay = "--overlay" in sys.argv
    os.makedirs(PREVIEW, exist_ok=True)
    for pg in all_pages():
        pg.render(overlay).convert("RGB").save(os.path.join(PREVIEW, pg.name + ".png"))
        print(pg.name)
