#!/usr/bin/env python3
"""Prophet '08 OS decoder (development tool; works on your own update files, ships nothing).

    p8_fw.py info    FILE.syx...            what each update file is
    p8_fw.py unpack  FILE.syx -o OUT.bin    the decoded image (local use only: never commit it)
    p8_fw.py tables  MAIN.syx VOICE.syx     the tables the engine's curves are fitted to, in physical units
    p8_fw.py basic   MAIN.syx               the firmware's Basic Patch against tools/gen_patch.py's init values
    p8_fw.py dis     FILE.syx START END     dsPIC listing (program addresses) through dspic_dis.py

Format (found 2026-10-07, docs/FIRMWARE.md): F0 01 23 <target> <payload> F7, target 0x6B = main CPU, 0x6C = voice CPU. The payload is the
manual's "packed MS bit" format restarted every 1171 MIDI bytes (1024 decoded bytes), as on the Poly Evolver and Tempest; each image ends
with one extra byte. Both decode to 131 073 bytes: a dsPIC (24-bit words stored as 3 bytes), reset GOTO 0x4D7C (main) and 0xFFBC (voice).
Strings and byte tables are kept one byte per word (the low byte of each 3-byte word); 16-bit tables are the low two bytes.
"""
import argparse
import os
import sys

TARGETS = {0x6B: "main CPU (dsPIC)", 0x6C: "voice CPU (dsPIC)"}


def unpack7(d):
    out = bytearray()
    for i in range(0, len(d), 8):
        m = d[i]
        for j, b in enumerate(d[i + 1:i + 8]):
            out.append(b | (((m >> j) & 1) << 7))
    return bytes(out)


def unpack_fw(path):
    d = open(path, "rb").read()
    if len(d) < 6 or d[:3] != b"\xf0\x01\x23" or d[-1] != 0xF7:
        sys.exit("%s: not a Prophet '08 update (F0 01 23 ... F7)" % path)
    body = d[4:-1]
    out = bytearray()
    for i in range(0, len(body), 1171):
        out += unpack7(body[i:i + 1171])
    return d[3], bytes(out)


def w16(img, a):
    """16-bit word at program address a (even)"""
    k = a // 2
    return img[3 * k] | img[3 * k + 1] << 8


def s16(x):
    return x - 65536 if x >= 32768 else x


def table16(img, a, n):
    return [w16(img, a + 2 * i) for i in range(n)]


def find_main(files):
    """-> (main image, voice image) from the two file paths in any order"""
    im = {}
    for f in files:
        t, img = unpack_fw(f)
        im[t] = img
    if 0x6B not in im or 0x6C not in im:
        sys.exit("need both the main (0x6B) and the voice (0x6C) update file")
    return im[0x6B], im[0x6C]


def simplify(pts, tol):
    """greedy piecewise-linear fit through (x, y) points, relative error <= tol; -> breakpoints"""
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = i + 1
        best = j
        while j < len(pts):
            (x0, y0), (x1, y1) = pts[i], pts[j]
            ok = all(abs(y0 + (x - x0) * (y1 - y0) / (x1 - x0) - y) <= tol * max(abs(y), 1) for x, y in pts[i:j + 1])
            if not ok:
                break
            best = j
            j += 1
        out.append(pts[best])
        i = best
    return out


def cmd_tables(a):
    main, voice = find_main(a.files)
    env = table16(voice, 0x6EC, 128)
    print("Envelope time table (voice 0x06EC, 128 entries), values 0..127 as times in ms (assumed unit): %d ... %d" % (env[0], env[-1]))
    print("  breakpoints (index, value), within 2 %%: %s" % simplify(list(enumerate(env)), 0.02))
    lin = table16(voice, 0x428, 99)
    print("0x0428: %d entries 655 x n (linear 0-100 to 0-65535): %s ... %s" % (len(lin), lin[:3], lin[-1]))
    t = table16(voice, 0x2F2, 101)
    print("0x02F2: 101 entries rising from 0 to 327 (also main 0x0B4C): %s" % simplify(list(enumerate(t)), 0.03))
    semi = table16(voice, 0x1342, 25)
    print("0x1342: %s (512 x 2^(k/12), two octaves)" % semi)
    base = None
    for k in range(0, len(main) // 3 - 24):
        win = [s16(w16(main, 2 * (k + i))) for i in range(24)]
        if win[8:11] == [-1, 1, 2] and win[16:19] == [2, -2, 4] and False:
            base = k
    # unison detune rows: the 24 signed words that start -1, 1, 2, -2 (cents)
    for k in range(0, len(main) // 3 - 24):
        win = [s16(w16(main, 2 * (k + i))) for i in range(24)]
        if win[:4] == [-1, 1, 2, -2] and win[8:10] == [2, -2]:
            print("Unison detune (main 0x%X), cents per voice 1-8: detune1 %s, detune2 %s, detune3 %s" % (2 * k, win[0:8], win[8:16], win[16:24]))
            break


def cmd_basic(a):
    t, img = unpack_fw(a.file)
    at = None
    for i in range(0, len(img) - 48, 1):
        if img[i:i + 3 * 11:3] == b"Basic Patch":
            at = i
            break
    if at is None:
        sys.exit("Basic Patch not found")
    prog = [img[at + 3 * (16 + i)] for i in range(120)]
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import gen_patch as g
    diff = [(i, prog[i], g.T[i][3]) for i in range(102) if i in g.T and prog[i] != g.T[i][3]]
    print("firmware Basic Patch vs gen_patch.py init values, differing (index, firmware, ours): %s" % diff)
    print("split point %d, keyboard mode %d" % (prog[118], prog[119]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("info"); p.add_argument("files", nargs="+")
    p = sp.add_parser("unpack"); p.add_argument("file"); p.add_argument("-o", required=True)
    p = sp.add_parser("tables"); p.add_argument("files", nargs=2)
    p = sp.add_parser("basic"); p.add_argument("file")
    p = sp.add_parser("dis"); p.add_argument("file"); p.add_argument("start"); p.add_argument("end")
    a = ap.parse_args()
    if a.cmd == "info":
        for f in a.files:
            t, img = unpack_fw(f)
            print("%s: target 0x%02X %s, %d bytes decoded, first word %s" % (f, t, TARGETS.get(t, "?"), len(img), img[:3].hex()))
    elif a.cmd == "unpack":
        t, img = unpack_fw(a.file)
        open(a.o, "wb").write(img)
    elif a.cmd == "tables": cmd_tables(a)
    elif a.cmd == "basic": cmd_basic(a)
    elif a.cmd == "dis":
        import dspic_dis, tempfile
        t, img = unpack_fw(a.file)
        W = [img[3 * i] | img[3 * i + 1] << 8 | img[3 * i + 2] << 16 for i in range(len(img) // 3)]
        dspic_dis.listing(W, int(a.start, 0), int(a.end, 0))


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    main()
