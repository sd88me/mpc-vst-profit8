#!/usr/bin/env python3
"""The Prophet '08 program format as one table: the 384 program bytes in the instrument's own SysEx order.

    gen_patch.py --params     -> vst/params.json  (VST parameter list; index = position, append only)
    gen_patch.py --header     -> src/patch_tab.h  (the engine's table: key, range, init value, display format)

Layout (manual p. 43-49, checked against the 256 factory programs, NOTES in docs/FIRMWARE.md):
  0-101    layer A voice parameters        200-301  layer B (the same 102, +200)
  118      split point (program-wide)      119      keyboard mode (0 normal, 1 stack, 2 split; program-wide)
  120-183  layer A sequencer, 4 tracks x 16 steps   320-383  layer B sequencer
  184-199  program name (16 ASCII characters)
Indices 102-117, 302-317 are unused. 95 and 96 are swapped against the manual's table: 95 is the unison mode (0-4) and 96 the
key mode (0-5): the factory programs' value ranges and the firmware's own Basic Patch both say so.
Init values are the Basic Patch (manual p. 55; the firmware holds the same: tools/fw/p8_fw.py basic compares).
"""
import json
import sys

LFO_SHAPES = ["Triangle", "Rev Saw", "Sawtooth", "Square", "Random"]
GLIDE_MODES = ["Fixed Rate", "Fixed Rate A", "Fixed Time", "Fixed Time A"]
CLKDIV = ["Half", "Quarter", "Eighth", "8 half", "8 swing", "8 trip", "16th", "16 half", "16 swing", "16 trip", "32nd", "32 trip", "64 trip"]
TRIGS = ["Normal", "Normal NoRst", "No Gate", "NoGate NoRst", "Key Step"]
UNISON = ["1 Voice", "All Voices", "Detune 1", "Detune 2", "Detune 3"]
KEYPRI = ["Low", "Low Retrig", "High", "High Retrig", "Last", "Last Retrig"]
_ARP = ["Up", "Down", "Up/Down", "Assign", "Random"]
ARPMODE = ["%s%s" % (("%d Oct " % o) if o > 1 else "", a) for o in (1, 2, 3) for a in _ARP]
KBDMODE = ["Normal", "Stack", "Split"]

DEST = ["Off", "Osc1 Freq", "Osc2 Freq", "Osc1&2 Freq", "Osc Mix", "Noise Level", "Osc1 PW", "Osc2 PW", "Osc1&2 PW", "Filter Freq",
        "Resonance", "Filter AudMod", "VCA Level", "Pan Spread", "LFO1 Freq", "LFO2 Freq", "LFO3 Freq", "LFO4 Freq", "LFOAll Freq",
        "LFO1 Amt", "LFO2 Amt", "LFO3 Amt", "LFO4 Amt", "LFOAll Amt", "FltEnv Amt", "AmpEnv Amt", "Env3 Amt", "EnvAll Amt",
        "Env1 Attack", "Env2 Attack", "Env3 Attack", "EnvAll Attk", "Env1 Decay", "Env2 Decay", "Env3 Decay", "EnvAll Dcy",
        "Env1 Release", "Env2 Release", "Env3 Release", "EnvAll Rel", "Mod1 Amt", "Mod2 Amt", "Mod3 Amt", "Mod4 Amt"]
SRC = ["Off", "Seq 1", "Seq 2", "Seq 3", "Seq 4", "LFO 1", "LFO 2", "LFO 3", "LFO 4", "Filter Env", "Amp Env", "Env 3", "Pitch Bend",
       "Mod Wheel", "Pressure", "Breath", "Foot", "Expression", "Velocity", "Note Num", "Noise"]
assert len(DEST) == 44 and len(SRC) == 21

def osc(n):
    return [("osc%d_freq" % n, "Osc%d Freq" % n, 120, 24, "note"), ("osc%d_fine" % n, "Osc%d Fine" % n, 100, 49 if n == 1 else 51, "cents"),
            ("osc%d_shape" % n, "Osc%d Shape" % n, 103, 1, "shape"), ("osc%d_glide" % n, "Osc%d Glide" % n, 127, 0, "int"),
            ("osc%d_key" % n, "Osc%d Keybd" % n, 1, 1, "onoff")]

def env(p, name, d, s):
    return [(p + "_delay", name + " Delay", 127, 0, "int"), (p + "_a", name + " Attack", 127, 0, "int"),
            (p + "_d", name + " Decay", 127, d, "int"), (p + "_s", name + " Sustain", 127, s, "int"),
            (p + "_r", name + " Release", 127, d, "int")]

def lfo(n):
    return [("lfo%d_freq" % n, "LFO%d Freq" % n, 166, 80, "lfof"), ("lfo%d_shape" % n, "LFO%d Shape" % n, 4, 0, LFO_SHAPES),
            ("lfo%d_amt" % n, "LFO%d Amt" % n, 127, 0, "int"), ("lfo%d_dest" % n, "LFO%d Dest" % n, 43, 0, DEST),
            ("lfo%d_sync" % n, "LFO%d KeySync" % n, 1, 0, "onoff")]

def mod(n):
    return [("mod%d_src" % n, "Mod%d Source" % n, 20, 0, SRC), ("mod%d_amt" % n, "Mod%d Amt" % n, 254, 127, "bi"),
            ("mod%d_dest" % n, "Mod%d Dest" % n, 43, 0, DEST)]

def ctl(k, name):
    return [(k + "_amt", name + " Amt", 254, 127, "bi"), (k + "_dest", name + " Dest", 43, 0, DEST)]

BASE = (osc(1) + osc(2) + [
    ("sync", "Sync 2>1", 1, 0, "onoff"), ("glide_mode", "Glide Mode", 3, 0, GLIDE_MODES), ("slop", "Osc Slop", 5, 2, "int"),
    ("osc_mix", "Osc Mix", 127, 64, "int"), ("noise", "Noise", 127, 0, "int"),
    ("lpf_freq", "LPF Freq", 164, 148, "int"), ("lpf_res", "Resonance", 127, 0, "int"), ("lpf_key", "LPF Key Amt", 127, 0, "int"),
    ("lpf_audmod", "Audio Mod", 127, 0, "int"), ("poles", "4 Pole", 1, 1, ["2 Pole", "4 Pole"]),
    ("fenv_amt", "FEnv Amt", 254, 127, "bi"), ("fenv_vel", "FEnv Velocity", 127, 0, "int")]
    + env("fenv", "FEnv", 0, 0) + [
    ("vca_level", "VCA Level", 127, 0, "int"), ("spread", "Pan Spread", 127, 0, "int"), ("voice_vol", "Voice Volume", 127, 127, "int"),
    ("vca_env", "VCA Env Amt", 127, 127, "int"), ("vca_vel", "VCA Velocity", 127, 0, "int")]
    + env("aenv", "AEnv", 64, 64)
    + lfo(1) + lfo(2) + lfo(3) + lfo(4) + [
    ("env3_dest", "Env3 Dest", 43, 0, DEST), ("env3_amt", "Env3 Amt", 254, 127, "bi"), ("env3_vel", "Env3 Velocity", 127, 0, "int")]
    + env("env3", "Env3", 0, 0)
    + mod(1) + mod(2) + mod(3) + mod(4) + [
    ("seq1_dest", "Seq1 Dest", 43, 0, DEST), ("seq2_dest", "Seq2 Dest", 43, 0, DEST), ("seq3_dest", "Seq3 Dest", 43, 0, DEST),
    ("seq4_dest", "Seq4 Dest", 43, 0, DEST)]
    + ctl("wheel", "ModWheel") + ctl("press", "Pressure") + ctl("breath", "Breath") + ctl("vel", "Velocity") + ctl("foot", "Foot") + [
    ("tempo", "BPM", 250, 120, "tempo"), ("clock_div", "Clock Div", 12, 2, CLKDIV), ("bend_range", "Bend Range", 12, 4, "int"),
    ("seq_trig", "Seq Trigger", 4, 0, TRIGS), ("unison_mode", "Unison Mode", 4, 2, UNISON), ("key_mode", "Unison Assign", 5, 0, KEYPRI),
    ("arp_mode", "Arp Mode", 14, 0, ARPMODE), ("env3_repeat", "Env3 Repeat", 1, 0, "onoff"), ("unison", "Unison", 1, 0, "onoff"),
    ("arp", "Arpeggiator", 1, 0, "onoff"), ("gseq", "Gated Seq", 1, 0, "onoff")])
assert len(BASE) == 102, len(BASE)
# the two program-wide bytes
GLOBAL = [(118, "split_point", "Split Point", 127, 60, "note"), (119, "kbd_mode", "Keyboard Mode", 2, 0, KBDMODE)]

# every byte of the program: (index, key, name, max, default, fmt); unused ones are skipped
def table():
    T = {}
    for layer, off, pre, npre in (("A", 0, "", "A "), ("B", 200, "b_", "B ")):
        for i, (k, n, mx, d, f) in enumerate(BASE):
            T[off + i] = (pre + k, npre + n, mx, d, f)
    for i, k, n, mx, d, f in GLOBAL: T[i] = (k, n, mx, d, f)
    for layer, off, pre in (("A", 120, "a"), ("B", 320, "b")):
        for t in range(4):
            for s in range(16):
                T[off + 16 * t + s] = ("%ss%d_%d" % (pre, t + 1, s + 1), "%s Seq%d Step%d" % (pre.upper(), t + 1, s + 1), 127 if t == 0 else 126, 0, "step%d" % (1 if t == 0 else 2))
    return T

T = table()
EXTRA = [
    {"key": "layer", "name": "Edit Layer", "options": ["A", "B"], "default": 0},
    {"key": "bank", "name": "Bank", "min": 0, "max": 63, "default": 0, "display": "int", "dynamic_display": True},
    {"key": "program", "name": "Program", "min": 0, "max": 127, "default": 0, "display": "int", "dynamic_display": True},
    {"key": "patch_name", "name": "Name", "min": 0, "max": 1, "default": 0, "display": "string"},
    {"key": "bank_name", "name": "Bank Name", "min": 0, "max": 1, "default": 0, "display": "string"},
    {"key": "seq_run", "name": "Seq Run", "options": ["Stop", "Run", "Transport"], "default": 0},
    {"key": "clock_src", "name": "Clock", "options": ["Program", "Host"], "default": 1},
    {"key": "status", "name": "Status", "min": 0, "max": 1, "default": 0, "display": "string"},
] + [{"key": "%s_%s" % (k, d), "name": "%s %s" % (k.title(), "<" if d == "prev" else ">"), "min": 0, "max": 1, "default": 0,
      "momentary": True, "type": "trigger", "step_of": k, "step_delta": -1 if d == "prev" else 1}
     for k in ("bank", "program") for d in ("prev", "next")] + [
    {"key": "quality", "name": "Quality", "options": ["Eco 1x", "High 2x", "Ultra 4x"], "default": 1}]

def params_json():
    out = []
    for i in sorted(T):
        key, name, mx, d, fmt = T[i]
        e = {"key": key, "name": name}
        if isinstance(fmt, list):
            e["options"] = fmt
            e["default"] = d
        else:
            e.update({"min": 30 if fmt == "tempo" else 0, "max": mx, "default": d, "display": "int"})
            if fmt != "int": e["dynamic_display"] = True
        out.append(e)
    return {"name": "Profit-8", "params": out + EXTRA}

def header():
    L = ["/* generated by tools/gen_patch.py: do not edit */", "#pragma once", "enum { NPATCH = 384, NBASE = 102 };",
         "typedef struct { const char *key; short min, max, def; const char *fmt; } ptab_t;", "static const ptab_t PTAB[NPATCH] = {"]
    for i in range(384):
        if i in T:
            key, name, mx, d, fmt = T[i]
            f = "opt" if isinstance(fmt, list) else fmt
            L.append('    {"%s", %d, %d, %d, "%s"},  /* %d */' % (key, 30 if f == "tempo" else 0, mx, d, f, i))
        else:
            L.append('    {"", 0, 0, 0, "unused"},  /* %d */' % i)
    L.append("};")
    L.append("static const char *const DEST_NAMES[44] = {%s};" % ", ".join('"%s"' % x for x in DEST))
    L.append("static const char *const SRC_NAMES[21] = {%s};" % ", ".join('"%s"' % x for x in SRC))
    for i in sorted(T):
        key, name, mx, d, fmt = T[i]
        if isinstance(fmt, list):
            L.append("static const char *const OPT_%s[] = {%s};" % (key.upper(), ", ".join('"%s"' % o for o in fmt)))
    L.append("static const char *const *const POPT[NPATCH] = {")
    for i in range(384):
        key, name, mx, d, fmt = T.get(i, ("", "", 0, 0, 0))
        L.append("    %s," % ("OPT_" + key.upper() if isinstance(fmt, list) else "0"))
    L.append("};")
    L.append("enum {")
    for i, (k, *_r) in enumerate(BASE): L.append("    P_%s = %d," % (k.upper(), i))
    L.append("    P_SPLIT_POINT = 118, P_KBD_MODE = 119, SEQ_A = 120, SEQ_B = 320, B_OFF = 200, NAME_AT = 184")
    L.append("};")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    if "--params" in sys.argv: print(json.dumps(params_json(), indent=1))
    elif "--header" in sys.argv: sys.stdout.write(header())
    else: sys.exit(__doc__)
