# What the Prophet '08 files hold

Findings from the two public OS updates (Main 2.3, Voice 1.5), the manual (v1.3) and the factory banks, decoded offline on 2026-10-07 with
`tools/fw/p8_fw.py`. Nothing here was checked against a running instrument. No firmware bytes, decoded images, tables or banks are committed:
the tools rebuild every number below from your own files.

## 1. The update format
`F0 01 23 <target> <payload> F7`: target `0x6B` main CPU, `0x6C` voice CPU. The payload is the manual's "packed MS bit" format restarted every
1171 MIDI bytes (1024 decoded bytes), as on the Poly Evolver and Tempest. Both files decode to 131 073 bytes (128 KB and one extra byte): a
dsPIC (24-bit words stored as 3 bytes), reset `GOTO 0x4D7C` (main) and `GOTO 0xFFBC` (voice). Strings and byte tables hold one byte in each 3-byte
word; 16-bit tables the low two bytes. `tools/fw/dspic_dis.py` (from the Tempest port) disassembles them (`p8_fw.py dis`).

## 2. What is not in them
- **No factory programs.** The only program in the main image is the Basic Patch (the "hold PROGRAM and hit +/YES" template). The factory banks are a
  separate SysEx download from DSI (`Prophet_08_Programs_v1.0.syx`: 256 programs, banks 0 and 1) and are loaded as banks at run time.
- **No waves.** The oscillators are analog; the plugin's oscillators and filter are models (`analog/mpc_analog.h`).
- The **Basic Patch** in the firmware equals this project's init values exactly (`p8_fw.py basic`, 2026-10-07).

## 3. The program format (manual p. 43-49 + the 512 programs we have)
384 bytes: layer A parameters 0-101, layer B the same at +200, split point (118) and keyboard mode (119, 0 normal / 1 stack / 2 split) for the whole
program, sequencer steps 120-183 (A) and 320-383 (B), the name at 184-199. A SysEx program dump is `F0 01 23 02 <bank> <prog> <439 packed bytes> F7`.
`tools/check_layout.py FILE.syx...` checks `tools/gen_patch.py`'s ranges: all 512 programs fit (2026-10-07).
**Indices 95 and 96 are swapped in the manual's table**: 95 is the unison mode (0-4), 96 the key mode / "unison assign" (0-5). Evidence: 96 holds 0-5 with
4 and 5 (last note) the commonest values in the factory programs, 95 holds 0-4, the manual's own text lists "Unison Assign" with the six key modes, and the
firmware's Basic Patch has 2 (detune 1) at 95. The manual lists arpeggiator modes 0-3 but the text has 15 (five patterns x 1-3 octaves): the plugin allows 0-14.

## 4. The main CPU (`p8_fw.py tables`)
- **Unison detune**: main 0x0D5E holds 3 x 8 signed words, cents per voice 1-8: detune 1 = -1 +1 +2 -2 -3 +3 +4 -4, detune 2 = +2 -2 +4 -4 -6 +6 -8 +8,
  detune 3 = -3 +3 -6 +6 -9 +9 -12 +12 (the Poly Evolver's table has the same -1/+1/-3/+3 start). The plugin uses them as written (`DETUNE` in `src/engine.c`).
- The 101-entry table 0,2,3,4 ... 327 at main 0x0B4C (also voice 0x02F2) and the linear 0-100 table (voice 0x0428) are not identified yet.

## 5. The voice CPU
- **Time table** (voice 0x06EC, 128 entries): 0, 10, 20 ... 500 at index 50, 540 ... 700 at 55, 1000 at 60, 1700 at 67, 2400 at 73, 3100 at 80, 10 700 at
  117, 14 500 at 127 (the table's own duplicate at 73/74). It is the only 128-entry increasing table with the shape of an envelope time, so the envelope
  parameters (0-127) are read through it as milliseconds. **The unit and the stage it serves are not proven**: the code that reads it was not found (it is not
  addressed through a plain `MOV #` of its PSV address). The plugin uses it for attack (linear ramp in that time), delay, and as the full-decay time of the
  exponential decay and release (time to fall to 1 %). `p8_env_seconds` in `src/curves.c` holds the breakpoints (within 2 %).
- Two decreasing 127-entry tables (voice 0x0FC0 area: 700, 600 ... 2; 0x10BE: 900, 700 ... 0) look like per-voice rate counts; the code at 0xA598 reads 0x10BE for
  two stages of a pair of states. Not used yet.
- 0x1342: 512 x 2^(k/12) over two octaves: a semitone ratio table (pitch CV).
- The voice CPU's RAM holds the calibration tables for the analog circuits (filter, oscillators), filled at start-up; the cutoff in Hz cannot come from the files.

## 6. What the engine assumes (not from the files)
- **LFO rates**: the Poly Evolver's scale (30 s at 0, round frequencies to 7.7 Hz at 89, semitones from 8.18 Hz at 90 to 261.6 Hz at 150), which the manual's text for
  the Prophet matches. Synced settings 151-166 are the manual's list (32 steps a cycle ... 16 cycles a step).
- **Filter**: 0-164 semitones from C0 (16.35 Hz), "more than 13 octaves"; envelope amount +127 sweeps the whole range, as the factory programs use it (cutoff 0,
  amount +127). Key amount 64 = one semitone a note about C3. Audio mod: oscillator 1 modulates the cutoff by up to 60 semitones (an estimate).
- **Modulation depth**: full source and amount sweep the destination's whole parameter range (`RANGE` in `src/engine.c`). Sequencer step values add their value in
  parameter units (a pitch step of 12 is an octave).
- **Glide, slop, pan spread positions, VCA curve**: estimates (glide 3 ms to 6 s per octave; slop up to 7.5 cents; spread positions by voice number).
