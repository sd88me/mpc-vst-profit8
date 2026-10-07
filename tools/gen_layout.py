#!/usr/bin/env python3
"""Writes vst/layout.conf, vst/images/wordmark.svg and vst/images/cheeks.svg.

The look takes its cues from the instrument's panel without copying it: a charcoal plate between two wood cheeks, thin pale section
outlines with caps titles, black pointer knobs, amber LEDs and a red two-line display. The tabs follow the panel's sections.
Geometry is absolute (plugin area x 0-1280, y 92-720): a control sits in a 140 px cell, a section row is 150 px tall. A page holds at most
16 Q-Link keys. Every control addresses the layer chosen with EDIT LAYER (the engine routes the keys), so one set of controls serves A and B."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VST = os.path.join(HERE, "..", "vst")
OUT = []
CELL, ROW = 140, 150

def emit(s): OUT.append(s)
def Y(i): return 92 + 154 * i
def tab(name):
    emit("\n[tab %s]" % name)
    emit("art file=images/cheeks.svg x=0 y=92 w=1280 h=628")
def qlinks(name, keys):
    assert len(keys) <= 16, (name, len(keys))
    emit('qlinks "%s" = %s' % (name, ",".join(keys)))

def section(x, y, title, rows):
    """rows: lists of (label, key); '~' = toggle (LED), '^' = popup, '' = knob, None = empty cell. Returns the keys in order."""
    n = max(len(r) for r in rows)
    w, h = CELL * n, ROW * len(rows) - 4
    emit('frame x=%d y=%d w=%d h=%d title="%s"' % (x, y, w, h, title))
    keys = []
    for ri, items in enumerate(rows):
        ry = y + ROW * ri
        for ci, it in enumerate(items):
            if it is None: continue
            label, key = it
            cx = x + CELL * ci + CELL // 2
            if key[0] == "~": emit('toggle cx=%d cy=%d label="%s" key=%s look=led' % (cx, ry + 64, label, key[1:]))
            elif key[0] == "^": emit('popup cx=%d cy=%d w=126 h=48 label="%s" key=%s' % (cx, ry + 96, label, key[1:]))
            else: emit('knob cx=%d cy=%d r=24 label="%s" key=%s' % (cx, ry + 56, label, key))
            keys.append(key.lstrip("~^"))
    return keys

HEADER = """# Profit-8 skin: a charcoal plate between wood cheeks, pale section outlines, black pointer knobs, amber LEDs and a red display, drawn
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

WORDMARK = '''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="100" viewBox="0 0 360 100">
<text x="8" y="66" font-family="Titillium Web, sans-serif" font-style="italic" font-weight="700" font-size="58" fill="#f2f2f4">profit<tspan fill="#ff9a1f">'8</tspan></text>
<text x="10" y="90" font-family="Titillium Web, sans-serif" font-weight="600" font-size="13" letter-spacing="5" fill="#9c9ca6">8 VOICE ANALOG SYNTHESIZER</text>
</svg>
'''
CHEEKS = '''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="628" viewBox="0 0 1280 628">
<defs><linearGradient id="w" x1="0" x2="1"><stop offset="0" stop-color="#6e3a1c"/><stop offset="0.5" stop-color="#8a4b25"/><stop offset="1" stop-color="#5a2f16"/></linearGradient></defs>
<rect x="0" y="0" width="10" height="628" fill="url(#w)"/><rect x="1270" y="0" width="10" height="628" fill="url(#w)"/>
</svg>
'''

def main():
    emit(HEADER)
    tab("PROGRAM")
    emit('frame x=10 y=92 w=1260 h=146 title="PROGRAM"')
    for x, label, key in ((20, "PROGRAM", "program"), (650, "BANK", "bank")):
        emit('stepper style=dotmatrix cx=%d cy=190 w=280 h=48 label="%s" key=%s' % (x + 150, label, key))
    emit('readout style=dotmatrix cx=470 cy=190 w=320 h=48 label="" key=patch_name')
    emit('readout style=dotmatrix cx=1095 cy=190 w=320 h=48 label="" key=bank_name')
    kb = section(10, Y(1), "KEYBOARD", [[("EDIT LAYER", "^layer"), ("KEYBOARD", "^kbd_mode"), ("SPLIT POINT", "split_point"),
                                         ("UNISON", "~unison"), ("UNISON MODE", "^unison_mode"), ("UNISON ASSIGN", "^key_mode")]])
    emit('art file=images/wordmark.svg x=870 y=%d w=360 h=100' % (Y(1) + 20))
    misc = section(10, Y(2), "MISC PARAMETERS", [[("VOICE VOLUME", "voice_vol"), ("OSC 1 KEY", "~osc1_key"), ("OSC 2 KEY", "~osc2_key"),
                                                  ("OSC SLOP", "slop"), ("GLIDE MODE", "^glide_mode"), ("PITCH BEND", "bend_range")]])
    sysm = section(855, Y(2), "SYSTEM", [[("CLOCK", "^clock_src"), ("QUALITY", "^quality"), ("SEQ RUN", "^seq_run")]])
    seq = section(10, Y(3), "ARPEGGIATOR / SEQUENCER", [[("ARPEGGIATOR", "~arp"), ("ARP MODE", "^arp_mode"), ("GATED SEQ", "~gseq"),
                                                         ("SEQ TRIGGER", "^seq_trig"), ("BPM", "tempo"), ("CLOCK DIVIDE", "^clock_div")]])
    emit('frame x=855 y=%d w=420 h=146 title="STATUS"' % Y(3))
    emit('readout style=dotmatrix cx=1065 cy=%d w=390 h=48 label="" key=status' % (Y(3) + 98))
    qlinks("Program", ["program", "bank", "layer", "kbd_mode", "split_point", "unison", "unison_mode", "key_mode",
                       "voice_vol", "slop", "glide_mode", "bend_range", "arp", "arp_mode", "gseq", "tempo"])
    qlinks("Seq", ["gseq", "seq_trig", "clock_div", "arp_mode", "osc1_key", "osc2_key", "clock_src", "quality"])

    tab("OSC")
    o1 = section(10, Y(0), "OSCILLATOR 1", [[("FREQUENCY", "osc1_freq"), ("FINE", "osc1_fine"), ("SHAPE/PW", "osc1_shape"), ("GLIDE", "osc1_glide"),
                                             ("KEYBOARD", "~osc1_key")]])
    o2 = section(10, Y(1), "OSCILLATOR 2", [[("FREQUENCY", "osc2_freq"), ("FINE", "osc2_fine"), ("SHAPE/PW", "osc2_shape"), ("GLIDE", "osc2_glide"),
                                             ("KEYBOARD", "~osc2_key")]])
    mx = section(730, Y(0), "MIX", [[("OSC MIX 1-2", "osc_mix"), ("NOISE", "noise"), ("SYNC 2>1", "~sync")]])
    qlinks("Osc", o1 + o2 + ["osc_mix", "noise", "sync"])

    tab("FILTER")
    lp = section(150, Y(0), "LOW PASS FILTER", [[("4 POLE", "~poles"), ("FREQUENCY", "lpf_freq"), ("RESONANCE", "lpf_res"), ("ENV AMOUNT", "fenv_amt"),
                                                 ("VELOCITY", "fenv_vel"), ("KEY AMOUNT", "lpf_key"), ("AUDIO MOD", "lpf_audmod")],
                                                [None, ("DELAY", "fenv_delay"), ("ATTACK", "fenv_a"), ("DECAY", "fenv_d"), ("SUSTAIN", "fenv_s"), ("RELEASE", "fenv_r")]])
    am = section(150, Y(0) + 320, "AMP", [[("VCA LEVEL", "vca_level"), ("ENV AMOUNT", "vca_env"), ("VELOCITY", "vca_vel"), ("PAN SPREAD", "spread")],
                                          [("DELAY", "aenv_delay"), ("ATTACK", "aenv_a"), ("DECAY", "aenv_d"), ("SUSTAIN", "aenv_s"), ("RELEASE", "aenv_r")]])
    qlinks("Filter", [k for k in lp if k != "poles"][:7] + ["poles"] + ["vca_level", "vca_env", "vca_vel", "spread", "voice_vol", "osc_mix", "noise"])
    qlinks("Filter Env", ["fenv_delay", "fenv_a", "fenv_d", "fenv_s", "fenv_r", "lpf_freq", "lpf_res", "fenv_amt"])
    qlinks("Amp Env", ["aenv_delay", "aenv_a", "aenv_d", "aenv_s", "aenv_r", "vca_level", "vca_env", "vca_vel"])

    tab("LFO")
    lf = []
    for n in range(4):
        k = section(9, Y(n), "LFO %d" % (n + 1), [[("FREQUENCY", "lfo%d_freq" % (n + 1)), ("SHAPE", "^lfo%d_shape" % (n + 1)),
                                                    ("AMOUNT", "lfo%d_amt" % (n + 1)), ("DESTINATION", "^lfo%d_dest" % (n + 1)), ("KEY SYNC", "~lfo%d_sync" % (n + 1))]])
        lf += k
    e3 = section(709, Y(0), "ENVELOPE 3", [[("DESTINATION", "^env3_dest"), ("AMOUNT", "env3_amt"), ("VELOCITY", "env3_vel"), ("DELAY", "env3_delay")],
                                           [("ATTACK", "env3_a"), ("DECAY", "env3_d"), ("SUSTAIN", "env3_s"), ("RELEASE", "env3_r")]])
    section(709, Y(2), "REPEAT", [[("ENV 3 REPEAT", "~env3_repeat")]])
    for n in range(4):
        qlinks("LFO %d" % (n + 1), lf[5 * n:5 * n + 5])
    qlinks("Env 3", e3)

    tab("MODS")
    mods = []
    for n in range(4):
        mods += section(10, Y(n), "MODULATOR %d" % (n + 1), [[("SOURCE", "^mod%d_src" % (n + 1)), ("DESTINATION", "^mod%d_dest" % (n + 1)), ("AMOUNT", "mod%d_amt" % (n + 1))]])
    fixed = []
    for i, (title, k) in enumerate([("MOD WHEEL", "wheel"), ("PRESSURE", "press"), ("BREATH", "breath"), ("VELOCITY", "vel"), ("FOOT CONTROLLER", "foot")]):
        fixed += section(450 + 300 * (i % 2), Y(i // 2), title, [[("AMOUNT", "%s_amt" % k), ("DESTINATION", "^%s_dest" % k)]])
    sd = section(450, Y(3), "SEQUENCE DESTINATIONS", [[("SEQ 1", "^seq1_dest"), ("SEQ 2", "^seq2_dest"), ("SEQ 3", "^seq3_dest"), ("SEQ 4", "^seq4_dest")]])
    qlinks("Mods", mods + ["wheel_amt", "wheel_dest", "press_amt", "press_dest"])
    qlinks("Controllers", fixed)
    qlinks("Seq Dest", sd)

    for pair in ((1, 2), (3, 4)):
        tab("SEQ %d-%d" % pair)
        for j, t in enumerate(pair):
            keys = []
            for half in range(2):
                items = [[("%d" % (8 * half + k + 1), "s%d_%d" % (t, 8 * half + k + 1)) for k in range(8)]]
                keys += section(80, Y(2 * j + half), "SEQUENCE %d  STEPS %d-%d" % (t, 8 * half + 1, 8 * half + 8), items)
            qlinks("Seq %d" % t, keys)

    os.makedirs(os.path.join(VST, "images"), exist_ok=True)
    open(os.path.join(VST, "layout.conf"), "w").write("\n".join(OUT) + "\n")
    open(os.path.join(VST, "images", "wordmark.svg"), "w").write(WORDMARK)
    open(os.path.join(VST, "images", "cheeks.svg"), "w").write(CHEEKS)

if __name__ == "__main__":
    main()
