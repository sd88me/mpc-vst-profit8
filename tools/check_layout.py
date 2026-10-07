#!/usr/bin/env python3
"""Checks tools/gen_patch.py's table against the user's own factory banks (Preset Banks folder or any .syx): every program byte
within its range, and prints the indices the table gets wrong. Usage: check_layout.py FILE.syx..."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gen_patch as g

def unpack(b):
    o = bytearray()
    for i in range(0, len(b), 8):
        m = b[i]
        for j, x in enumerate(b[i + 1:i + 8]): o.append(x | ((m >> j & 1) << 7))
    return bytes(o)

bad = {}
n = 0
for f in sys.argv[1:]:
    for m in open(f, "rb").read().split(b"\xf7"):
        if len(m) < 440 or m[:4] != b"\xf0\x01\x23\x02": continue
        p = unpack(m[6:])
        n += 1
        for i in range(384):
            if i in g.T and p[i] > g.T[i][2]: bad.setdefault(i, []).append(p[i])
for i in sorted(bad): print("index", i, g.T[i][0], "max", g.T[i][2], "seen up to", max(bad[i]), "in", len(bad[i]), "programs")
print("%d programs, %d indices out of range" % (n, len(bad)))
