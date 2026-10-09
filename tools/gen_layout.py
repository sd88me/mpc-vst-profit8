#!/usr/bin/env python3
"""Writes vst/layout.conf. The art it refers to is static: vst/images/metal.svg (the brushed plate), cheeks.svg (the wood) and wordmark.svg
(tools/make_wordmark.py).

The look takes its cues from the instrument's panel without copying it: a brushed black plate between two wood cheeks, thin pale section
outlines with caps titles, black pointer knobs, amber LEDs and a red display. The tabs follow the panel's sections.
Geometry is absolute (plugin area x 0-1280, y 92-720). The wood cheeks cover x 0-17 and 1263-1280, so every panel stays inside
x 20-1260 and y 92-712; the build fails if one does not, or if two overlap (`check()`). A control sits in a 136 px cell (MPC's value box under
a knob is 130 px wide), a section row is 150 px tall. A page holds at most 16 Q-Link keys. Every control addresses the layer chosen with
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

def section(x, y, title, rows, cw=None):
    """rows: lists of (label, key); '~' = toggle (LED), '^' = popup, '' = knob, None = empty cell. cw: column widths (default CELL).
    Returns the keys in order."""
    n = max(len(r) for r in rows)
    cw = cw or [CELL] * n
    w, h = sum(cw[:n]), ROW * len(rows) - 4
    frame(x, y, w, h, title)
    keys = []
    for ri, items in enumerate(rows):
        ry = y + ROW * ri
        for ci, it in enumerate(items):
            if it is None: continue
            label, key = it
            cx = x + sum(cw[:ci]) + cw[ci] // 2
            if key[0] == "~": emit('toggle cx=%d cy=%d label="%s" key=%s look=led' % (cx, ry + 64, label, key[1:]))
            elif key[0] == "^": emit('popup cx=%d cy=%d w=126 h=48 label="%s" key=%s' % (cx, ry + 96, label, key[1:]))
            else: emit('knob cx=%d cy=%d r=24 label="%s" key=%s' % (cx, ry + 56, label, key))
            keys.append(key.lstrip("~^"))
    return keys

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
art_css=skin.css"""

def main():
    emit(HEADER)

    tab("PROGRAM")
    frame(20, 92, 1240, 146, "PROGRAM")
    emit('stepper style=dotmatrix cx=330 cy=190 w=560 h=48 label="PROGRAM" key=program get=patch_name prev=program_prev next=program_next persistent=1')
    emit('stepper style=dotmatrix cx=950 cy=190 w=560 h=48 label="BANK" key=bank get=bank_name prev=bank_prev next=bank_next persistent=1')
    section(20, Y(1), "KEYBOARD", [[("EDIT LAYER", "^layer"), ("KEYBOARD", "^kbd_mode"), ("SPLIT POINT", "split_point"),
                                    ("UNISON", "~unison"), ("UNISON MODE", "^unison_mode"), ("UNISON ASSIGN", "^key_mode")]])
    emit('art file=images/wordmark.svg x=880 y=%d w=360 h=124' % (Y(1) + 10))
    section(20, Y(2), "MISC PARAMETERS", [[("VOICE VOLUME", "voice_vol"), ("OSC 1 KEY", "~osc1_key"), ("OSC 2 KEY", "~osc2_key"),
                                           ("OSC SLOP", "slop"), ("GLIDE MODE", "^glide_mode"), ("PITCH BEND", "bend_range")]])
    section(852, Y(2), "SYSTEM", [[("CLOCK", "^clock_src"), ("QUALITY", "^quality"), ("SEQ RUN", "^seq_run")]])
    section(20, Y(3), "ARPEGGIATOR / SEQUENCER", [[("ARPEGGIATOR", "~arp"), ("ARP MODE", "^arp_mode"), ("GATED SEQ", "~gseq"),
                                                   ("SEQ TRIGGER", "^seq_trig"), ("BPM", "tempo"), ("CLOCK DIVIDE", "^clock_div")]])
    frame(852, Y(3), 408, 146, "STATUS")
    emit('readout style=dotmatrix cx=1056 cy=%d w=380 h=48 label="" key=status' % (Y(3) + 98))
    qlinks("Program", ["program", "bank", "layer", "kbd_mode", "split_point", "unison", "unison_mode", "key_mode",
                       "voice_vol", "slop", "glide_mode", "bend_range", "arp", "arp_mode", "gseq", "tempo"])
    qlinks("Seq", ["gseq", "seq_trig", "clock_div", "arp_mode", "osc1_key", "osc2_key", "clock_src", "quality"])

    tab("BANKS")
    emit('stepper cx=181 cy=128 w=290 h=50 label="" key=browse_bank_index prev=prev_browse_bank next=next_browse_bank get=browse_bank_name style=dotmatrix')
    emit('stepper cx=640 cy=128 w=600 h=50 label="" key=program get=patch_name prev=program_prev next=program_next style=dotmatrix')
    emit('stepper cx=1119 cy=128 w=250 h=50 label="" key=patch_page_index prev=patch_page_prev next=patch_page_next get=patch_page_text style=dotmatrix')
    frame(20, 168, 300, 544, "BANKS")
    emit('list x=36 y=220 w=268 h=467 cols=1 rows=11 gap=6 th=37 key=bank_slot order=cols')
    frame(332, 168, 928, 544, "PROGRAMS")
    emit('list x=348 y=220 w=896 h=466 cols=3 rows=15 gap=3 th=28 key=patch_slot order=cols')
    qlinks("Banks", ["browse_bank_index", "program", "patch_page_prev", "patch_page_next"])

    tab("OSC FILTER")
    o1 = section(20, Y(0), "OSCILLATOR 1", [[("FREQUENCY", "osc1_freq"), ("FINE", "osc1_fine"), ("SHAPE/PW", "osc1_shape"), ("GLIDE", "osc1_glide"),
                                             ("KEYBOARD", "~osc1_key")]])
    o2 = section(20, Y(1), "OSCILLATOR 2", [[("FREQUENCY", "osc2_freq"), ("FINE", "osc2_fine"), ("SHAPE/PW", "osc2_shape"), ("GLIDE", "osc2_glide"),
                                             ("KEYBOARD", "~osc2_key")]])
    section(708, Y(0), "MIX", [[("OSC MIX 1-2", "osc_mix"), ("NOISE", "noise"), ("SYNC 2>1", "~sync")]])
    lp = section(20, Y(2), "LOW PASS FILTER", [[("4 POLE", "~poles"), ("FREQUENCY", "lpf_freq"), ("RESONANCE", "lpf_res"), ("ENV AMOUNT", "fenv_amt"),
                                                ("VELOCITY", "fenv_vel"), ("KEY AMOUNT", "lpf_key"), ("AUDIO MOD", "lpf_audmod")],
                                               [None, ("DELAY", "fenv_delay"), ("ATTACK", "fenv_a"), ("DECAY", "fenv_d"), ("SUSTAIN", "fenv_s"), ("RELEASE", "fenv_r")]])
    qlinks("Osc", o1 + o2 + ["osc_mix", "noise", "sync"])
    qlinks("Filter", ["lpf_freq", "lpf_res", "fenv_amt", "fenv_vel", "lpf_key", "lpf_audmod", "poles", "osc_mix"])
    qlinks("Filter Env", ["fenv_delay", "fenv_a", "fenv_d", "fenv_s", "fenv_r", "lpf_freq", "lpf_res", "fenv_amt"])

    tab("AMP LFO")
    section(20, Y(0), "AMP", [[("VCA LEVEL", "vca_level"), ("ENV AMOUNT", "vca_env"), ("VELOCITY", "vca_vel"), ("DELAY", "aenv_delay")],
                              [("ATTACK", "aenv_a"), ("DECAY", "aenv_d"), ("SUSTAIN", "aenv_s"), ("RELEASE", "aenv_r")]])
    section(572, Y(0), "EXTRA", [[("PAN SPREAD", "spread")], [("ENV 3 REPEAT", "~env3_repeat")]])
    section(716, Y(0), "ENVELOPE 3", [[("DESTINATION", "^env3_dest"), ("AMOUNT", "env3_amt"), ("VELOCITY", "env3_vel"), ("DELAY", "env3_delay")],
                                      [("ATTACK", "env3_a"), ("DECAY", "env3_d"), ("SUSTAIN", "env3_s"), ("RELEASE", "env3_r")]])
    lf = []
    lw = [130, 130, 130, 130, 96]     # two panels of 616 fill the 1240 between the cheeks
    for n in range(4):
        x = 20 if n % 2 == 0 else 644
        lf += section(x, Y(2 + n // 2), "LFO %d" % (n + 1), [[("FREQUENCY", "lfo%d_freq" % (n + 1)), ("SHAPE", "^lfo%d_shape" % (n + 1)),
                      ("AMOUNT", "lfo%d_amt" % (n + 1)), ("DESTINATION", "^lfo%d_dest" % (n + 1)), ("SYNC", "~lfo%d_sync" % (n + 1))]], cw=lw)
    qlinks("Amp", ["vca_level", "vca_env", "vca_vel", "aenv_delay", "aenv_a", "aenv_d", "aenv_s", "aenv_r", "spread"])
    qlinks("Env 3", ["env3_dest", "env3_amt", "env3_vel", "env3_delay", "env3_a", "env3_d", "env3_s", "env3_r", "env3_repeat"])
    for n in range(4):
        qlinks("LFO %d" % (n + 1), lf[5 * n:5 * n + 5])

    tab("MODS")
    mods = []
    for n in range(4):
        mods += section(20, Y(n), "MODULATOR %d" % (n + 1), [[("SOURCE", "^mod%d_src" % (n + 1)), ("DESTINATION", "^mod%d_dest" % (n + 1)), ("AMOUNT", "mod%d_amt" % (n + 1))]],
                        cw=[152] * 3)
    fixed = []
    for i, (title, k) in enumerate([("MOD WHEEL", "wheel"), ("PRESSURE", "press"), ("BREATH", "breath"), ("VELOCITY", "vel"), ("FOOT CONTROLLER", "foot")]):
        fixed += section(488 + 392 * (i % 2), Y(i // 2), title, [[("AMOUNT", "%s_amt" % k), ("DESTINATION", "^%s_dest" % k)]], cw=[190, 190])
    sd = section(488, Y(3), "SEQUENCE DESTINATIONS", [[("SEQ 1", "^seq1_dest"), ("SEQ 2", "^seq2_dest"), ("SEQ 3", "^seq3_dest"), ("SEQ 4", "^seq4_dest")]],
                 cw=[193] * 4)
    qlinks("Mods", mods + ["wheel_amt", "wheel_dest", "press_amt", "press_dest"])
    qlinks("Controllers", fixed)
    qlinks("Seq Dest", sd)

    for pair in ((1, 2), (3, 4)):
        tab("SEQ %d-%d" % pair)
        for j, t in enumerate(pair):
            rows = [[("%d" % (8 * half + k + 1), "s%d_%d" % (t, 8 * half + k + 1)) for k in range(8)] for half in range(2)]
            keys = section(96, Y(2 * j), "SEQUENCE %d" % t, rows)
            qlinks("Seq %d" % t, keys)

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
