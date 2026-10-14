#!/usr/bin/env python3
"""Writes vst/layout.conf. The art it refers to is static: vst/images/metal.svg (the brushed plate), cheeks.svg (the wood) and wordmark.svg
(tools/make_wordmark.py).

The look takes its cues from the instrument's panel without copying it: a brushed black plate between two wood cheeks, thin pale section
outlines with caps titles, black pointer knobs, amber LEDs and a red display. The tabs follow the panel's sections.
Geometry is absolute (plugin area x 0-1280, y 92-720). The wood cheeks cover x 0-17 and 1263-1280, so every panel stays inside
x 20-1260 and y 92-712; the build fails if one does not, or if two overlap (`check()`). A control sits in a 136 px cell (MPC's value box under
a knob is 130 px wide), a section row is 150 px tall. A page holds at most 16 Q-Link keys; MPC outlines the column the
Q-Links drive (qlink_bounds=column), so each column of four stays inside one panel, or two small panels side by side. Every control addresses the layer chosen with
EDIT LAYER (the engine routes the keys), so one set of controls serves A and B."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VST = os.path.join(HERE, "..", "vst")
OUT = []
CELL, ROW = 136, 150
X0, X1, Y0, Y1 = 20, 1260, 92, 712
FRAMES = {}      # tab -> [(x, y, w, h, title)]
CUR = [None]

def emit(s): OUT.append(s)
def Y(i): return 92 + 154 * i
def tab(name):
    CUR[0] = name
    FRAMES[name] = []
    emit("\n[tab %s]" % name)
    emit("art file=images/metal.svg x=0 y=92 w=1280 h=628")
def qlinks(name, keys):
    assert len(keys) <= 16, (name, len(keys))
    emit('qlinks "%s" = %s' % (name, ",".join(keys)))

def frame(x, y, w, h, title):
    FRAMES[CUR[0]].append((x, y, w, h, title))
    emit('frame x=%d y=%d w=%d h=%d title="%s"' % (x, y, w, h, title))

def check():
    """every panel inside the safe area, no two overlapping, on each page"""
    for t, fr in FRAMES.items():
        for i, (x, y, w, h, n) in enumerate(fr):
            assert X0 <= x and x + w <= X1 and Y0 <= y and y + h <= Y1, "%s: panel %r runs off the page (%d,%d %dx%d)" % (t, n, x, y, w, h)
            for (x2, y2, w2, h2, n2) in fr[i + 1:]:
                assert x + w <= x2 or x2 + w2 <= x or y + h <= y2 or y2 + h2 <= y, "%s: panels %r and %r overlap" % (t, n, n2)

def control(cx, ry, label, key, r=24):
    """one control in a 146 px row whose top is ry: '~' = toggle (LED), '^' = popup, '' = knob. Returns its key."""
    if key[0] == "~": emit('toggle cx=%d cy=%d label="%s" key=%s look=led' % (cx, ry + 64, label, key[1:]))
    elif key[0] == "^": emit('popup cx=%d cy=%d w=126 h=48 label="%s" key=%s' % (cx, ry + 96, label, key[1:]))
    else: emit('knob cx=%d cy=%d r=%d label="%s" key=%s' % (cx, ry + 56, r, label, key))
    return key.lstrip("~^")

def panel(x, y, w, h, title, items, corner=None):
    """One Q-Link group: a panel with a row of up to four controls (label, key), centred in it; MPC outlines it while
    the Q-Links drive it. corner: an on/off switch (label, key) in the top right, touch only (not one of the four).
    Returns the group's four Q-Link slots, '-' for an empty one."""
    assert len(items) <= 4, (title, len(items))
    frame(x, y, w, h, title)
    cw = min(154, w // max(len(items), 1))
    x0, ry = x + (w - cw * len(items)) // 2, y + (h - 146) // 2
    big = h >= 200
    keys = [control(x0 + cw * i + cw // 2, ry + (12 if big else 0), lab, k, r=30 if big else 24) for i, (lab, k) in enumerate(items)]
    if corner:
        emit('toggle cx=%d cy=%d label="%s" key=%s look=led' % (x + w - 74, y + 34, corner[0], corner[1]))
    return keys + ["-"] * (4 - len(keys))

QX, QY, QW, QH = (20, 644), (Y(0), Y(2)), 616, 296   # the 2 x 2 grid: a page's four panels, one per Q-Link column

def grid_page(name, groups):
    """A page of up to four Q-Link groups, (title, items[, corner]) each, in a 2 x 2 grid read left to right, top to
    bottom: Q-Link columns 1-4, so the page has one Q-Link set and every group is one outlined panel. An empty quarter
    shows the wordmark."""
    tab(name)
    keys = []
    for i in range(4):
        x, y = QX[i % 2], QY[i // 2]
        if i < len(groups):
            keys += panel(x, y, QW, QH, *groups[i])
        else:
            emit('art file=images/wordmark.svg x=%d y=%d w=360 h=124' % (x + (QW - 360) // 2, y + (QH - 124) // 2))
    qlinks(name, keys)

HEADER = """# Profit-08 skin: a charcoal plate between wood cheeks, pale section outlines, black pointer knobs, amber LEDs and a red display, drawn
# as our own motif (no logos, no traced panel art). Written by tools/gen_layout.py: do not edit.
theme_bg=1b1b1e
theme_panel=232327
theme_line=8d8d96
theme_box=1a1a1d
theme_ink=ffffff
theme_ink_dim=d9d9de
theme_ink_faint=9c9ca6
theme_accent=ff9a1f
theme_accent_hi=ff3a2a
theme_knob_face=111113
theme_knob_ring=050506
theme_knob_dot=ffffff
knob_look=prophet
theme_seg_active=ff3a2a
theme_seg_active_tx=ffffff
theme_seg_inactive=2c2c31
theme_btn_bg=bfc0c8
theme_btn_text=15161a
theme_btn_text_plain=15161a
theme_display_bg=1d0504
theme_display_cell=240706
theme_display_ink=ff4a35
theme_display_off=3b0f0b
theme_display_bezel=0c0c0e
theme_lcd=1d0504
art_css=skin.css
qlink_bounds=column"""

def main():
    emit(HEADER)

    tab("PROGRAM")
    frame(20, 92, 1240, 146, "PROGRAM")
    emit('stepper style=dotmatrix cx=330 cy=190 w=560 h=48 label="PROGRAM" key=program get=patch_name prev=program_prev next=program_next persistent=1')
    emit('stepper style=dotmatrix cx=950 cy=190 w=560 h=48 label="BANK" key=bank get=bank_name prev=bank_prev next=bank_next persistent=1')
    keys = ["program", "bank", "-", "-"]
    keys += panel(20, 246, 616, 150, "LAYERS", [("EDIT LAYER", "^layer"), ("KEYBOARD", "^kbd_mode"), ("SPLIT POINT", "split_point")])
    keys += panel(644, 246, 616, 150, "UNISON", [("UNISON", "~unison"), ("UNISON MODE", "^unison_mode"), ("UNISON ASSIGN", "^key_mode")])
    keys += panel(20, 404, 616, 150, "VOICE", [("VOICE VOLUME", "voice_vol"), ("PAN SPREAD", "spread"), ("PITCH BEND", "bend_range"),
                                                ("QUALITY", "^quality")])
    frame(20, 562, 616, 150, "STATUS")   # rows of 150: room under each knob for its value, inside the Q-Link outline
    emit('readout style=dotmatrix cx=328 cy=662 w=580 h=48 label="" key=status')
    emit('art file=images/wordmark.svg x=772 y=490 w=360 h=124')
    qlinks("PROGRAM", keys)

    tab("BANKS")
    emit('stepper cx=181 cy=128 w=290 h=50 label="" key=browse_bank_index prev=prev_browse_bank next=next_browse_bank get=browse_bank_name style=dotmatrix')
    emit('stepper cx=640 cy=128 w=600 h=50 label="" key=program get=patch_name prev=program_prev next=program_next style=dotmatrix')
    emit('stepper cx=1119 cy=128 w=250 h=50 label="" key=patch_page_index prev=patch_page_prev next=patch_page_next get=patch_page_text style=dotmatrix')
    frame(20, 168, 300, 544, "BANKS")
    emit('list x=36 y=220 w=268 h=467 cols=1 rows=11 gap=6 th=37 key=bank_slot order=cols')
    frame(332, 168, 928, 544, "PROGRAMS")
    emit('list x=348 y=220 w=896 h=466 cols=3 rows=15 gap=3 th=28 key=patch_slot order=cols')
    qlinks("BANKS", ["browse_bank_index", "program", "patch_page_index"])

    osc = lambda n: [("FREQUENCY", "osc%d_freq" % n), ("FINE", "osc%d_fine" % n), ("SHAPE/PW", "osc%d_shape" % n), ("GLIDE", "osc%d_glide" % n)]
    grid_page("OSC", [("OSCILLATOR 1", osc(1)), ("OSCILLATOR 2", osc(2)),
                      ("MIX", [("OSC MIX 1-2", "osc_mix"), ("NOISE", "noise"), ("SYNC 2>1", "~sync"), ("OSC SLOP", "slop")]),
                      ("KEYS & GLIDE", [("OSC 1 KEY", "~osc1_key"), ("OSC 2 KEY", "~osc2_key"), ("GLIDE MODE", "^glide_mode")])])

    adsr = lambda p: [("ATTACK", p + "_a"), ("DECAY", p + "_d"), ("SUSTAIN", p + "_s"), ("RELEASE", p + "_r")]
    grid_page("FILTER", [("LOW PASS FILTER", [("FREQUENCY", "lpf_freq"), ("RESONANCE", "lpf_res"), ("KEY AMOUNT", "lpf_key"), ("4 POLE", "~poles")]),
                         ("FILTER MOD", [("ENV AMOUNT", "fenv_amt"), ("VELOCITY", "fenv_vel"), ("ENV DELAY", "fenv_delay"), ("AUDIO MOD", "lpf_audmod")]),
                         ("FILTER ENVELOPE", adsr("fenv"))])

    grid_page("AMP", [("AMP", [("VCA LEVEL", "vca_level"), ("ENV AMOUNT", "vca_env"), ("VELOCITY", "vca_vel"), ("ENV DELAY", "aenv_delay")]),
                      ("AMP ENVELOPE", adsr("aenv")),
                      ("ENVELOPE 3", [("DESTINATION", "^env3_dest"), ("AMOUNT", "env3_amt"), ("VELOCITY", "env3_vel"), ("DELAY", "env3_delay")],
                       ("REPEAT", "env3_repeat")),
                      ("ENV 3 ENVELOPE", adsr("env3"))])

    grid_page("LFO", [("LFO %d" % n, [("FREQUENCY", "lfo%d_freq" % n), ("SHAPE", "^lfo%d_shape" % n), ("AMOUNT", "lfo%d_amt" % n),
                                       ("DESTINATION", "^lfo%d_dest" % n)], ("SYNC", "lfo%d_sync" % n)) for n in range(1, 5)])

    grid_page("MODS", [("MODULATOR %d" % n, [("SOURCE", "^mod%d_src" % n), ("DESTINATION", "^mod%d_dest" % n), ("AMOUNT", "mod%d_amt" % n)])
                       for n in range(1, 5)])

    pair = lambda a, b, ka, kb: [(a + " AMT", ka + "_amt"), (a + " DEST", "^" + ka + "_dest"), (b + " AMT", kb + "_amt"), (b + " DEST", "^" + kb + "_dest")]
    grid_page("CTRL", [("MOD WHEEL / PRESSURE", pair("WHEEL", "PRESS", "wheel", "press")),
                       ("BREATH / VELOCITY", pair("BREATH", "VELO", "breath", "vel")),
                       ("FOOT CONTROLLER", [("AMOUNT", "foot_amt"), ("DESTINATION", "^foot_dest")])])

    grid_page("ARP SEQ", [("ARPEGGIATOR", [("ARPEGGIATOR", "~arp"), ("ARP MODE", "^arp_mode")]),
                          ("GATED SEQUENCER", [("GATED SEQ", "~gseq"), ("SEQ TRIGGER", "^seq_trig"), ("SEQ RUN", "^seq_run")]),
                          ("CLOCK", [("CLOCK", "^clock_src"), ("BPM", "tempo"), ("CLOCK DIVIDE", "^clock_div")]),
                          ("SEQUENCE DESTINATIONS", [("SEQ %d" % n, "^seq%d_dest" % n) for n in range(1, 5)])])

    for t in range(1, 5):   # a page per sequence: its 16 steps, four to a Q-Link column
        grid_page("SEQ %d" % t, [("STEPS %d-%d" % (q + 1, q + 4), [("%d" % (q + k + 1), "s%d_%d" % (t, q + k + 1)) for k in range(4)])
                                 for q in (0, 4, 8, 12)])

    check()
    # the cheeks go last on each page, over the edge of the sections
    res = []
    first = True
    for ln in OUT:
        for sub in ln.split("\n"):
            if sub.startswith("[tab") and not first: res.append("art file=images/cheeks.svg x=0 y=92 w=1280 h=628")
            if sub.startswith("[tab"): first = False
            res.append(sub)
    res.append("art file=images/cheeks.svg x=0 y=92 w=1280 h=628")
    open(os.path.join(VST, "layout.conf"), "w").write("\n".join(res) + "\n")

if __name__ == "__main__":
    main()
