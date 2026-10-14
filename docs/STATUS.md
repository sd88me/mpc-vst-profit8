# Status (2026-10-07)

## Done (offline)
- Firmware tools (`tools/fw/p8_fw.py`), program layout table (`tools/gen_patch.py`, checked against 512 programs), 347 VST parameters.
- Engine (`src/engine.c`): 8 voices, two layers with normal / stack / split keyboard modes, poly and unison (1 voice, all voices, three detune sets from the
  firmware), per-oscillator glide, sync 2 > 1, analog oscillators (saw, triangle, saw-tri, pulse 0-99 off at the extremes), 2/4-pole OTA lowpass with envelope,
  velocity, key, audio mod, VCA, pan spread, three DADSR envelopes, four LFOs, four mod slots, the five controller routes, the 4 x 16 gated sequencer with all
  trigger modes, the arpeggiator (five patterns, 1-3 octaves), the bank loader (Preset_Banks folder).
- Analog section (shared `analog/mpc_analog.h`): Eco 1x or High 2x (Quality). The filter's self-oscillation tuning compensation from the shared header is applied in both:
  self-oscillation lands within 0.15 semitone of the set cutoff at 1 kHz (test_engine).
- Tests: `test/test_engine.c` (pitch, self-oscillation, silence after release, all 640 programs of the three banks: none clip, 2 silent) and
  `tools/test_port.sh vst/vst.json` (all pass but the known wheel-click rounding on a 0-120 range, as Morpho-PE; wrapper fix proposed separately).

- Banks page (2026-10-07, like the JV-880 port; offline): browse stepper (data wheel / Q-Link / arrows), 2 x 11 bank list (22 banks a window, follows the browsed bank), 2 x 14 program list with 5 pages; a bank tile only browses, a program tile loads it (bank and program follow the cursor). Q-Links: browse bank, program, program page (2026-10-13: the page stepper instead of the page - / page + buttons). `test_engine` covers it; tile text is live, so previews show empty tiles.
- Skin (2026-10-08, offline preview only): 7 tabs (Program, Banks, Osc + Filter, Amp + Envelope 3 + LFOs, Mods, Seq 1-2, Seq 3-4; 19 Q-Link pages), brushed black metal plate and wood cheeks (static `images/metal.svg`, `cheeks.svg`), flat wordmark. Panels stay inside x 20-1260 (clear of the cheeks) and `tools/gen_layout.py` fails the build if one overflows or overlaps. The Banks page has one bank column (11 slots) and three program columns (45 slots, 3 pages). Each sequencer is one panel of 16 steps. Renamed Profit-08 on 2026-10-08.
- Q-Link mapping (2026-10-13, MPC Live II): one Q-Link set per page, so a 4-knob MPC reaches everything on the screen it shows
  (MPC showed each page's further sets as sub-pages of the same screen). 13 pages: Program, Banks, Osc, Filter, Amp (with envelope 3),
  LFO, Mods, Ctrl (the controller routes), Arp Seq (with the sequence destinations), Seq 1-4. Each page is up to four panels in a 2 x 2
  grid, read left to right, top to bottom = Q-Link columns 1-4, of up to four controls each; with `qlink_bounds=column` MPC outlines the
  column the Q-Links drive. The LFO sync and envelope 3 repeat switches sit in their panel's corner, touch only. Projects saved with the
  earlier layout keep its Q-Link assignments (MPC stores them in the project) until the plugin is inserted again.
  charcoal plate, wood cheeks, red display, Q-Link pages per section. One set of controls serves both layers: the plain keys address the layer chosen with EDIT LAYER
  (`b_` keys are always layer B), so Q-Links follow the visible layer; the layer is part of the saved state.
- armhf build (`tools/build_port.sh`, 2026-10-07): 116 KB, highest glibc 2.27.

- Release package (2026-10-07, rebuilt after the level change): `Profit-08-0.1.0-mpc-armv7.zip` made with `release.py --id profit-08 --repo sd88me/mpc-vst-profit8 --license MIT --user-data Preset_Banks`; `catalog_check.py --catalog` OK; MPC OS 3.x only (the skin format). Bench on the Force (Eco): WARN, p99 34.0 % (the Q-Link sweep; 8 voices about 15 %). The banks folder is `Preset_Banks` because the installer's user-data path takes no spaces; `Preset Banks` is read too.

- Output level (2026-10-07, device): the first build was quiet (factory programs, one note: median peak 0.066). Master gain 0.3 -> 1.6 with a soft limiter (`ma_tanh`) instead of a hard clip. Bench peaks on the Force (same chord pattern, each plugin's default patch; 1 / 4 / 8 voices): Profit-08 0.35 / 0.85 / 0.96, Sturm 0.54 / 1.00 / 1.00, Clementine-XT 0.26 / 0.44 / 0.51, Maze Voice 0.17 / 0.24 / 0.21. The stock Odyssey is built into MPC and cannot be benched; compare it by ear. `P8_MASTER` in `src/engine.c` sets the level. RMS (average loudness, 1 / 4 / 8 voices, same patterns): Sturm 0.220 / 0.283 / 0.409, Profit-08 0.100 / 0.180 / 0.235, Clementine-XT 0.066 / 0.086 / 0.105, Maze Voice 0.063 / 0.079 / 0.076. Then Profit-08's master was lowered 2 dB (1.6 -> 1.27) and Sturm's 7 dB (with a soft limiter) to bring them closer together.

## Not done
- Device: install, bench (docs/BENCH.md), play, save/reload, Q-Links, MPC OS 2.x shape (nothing deployed yet).
- Drone (VCA level above 0 with no key held) is not modelled: a voice sounds only while gated or releasing.
- MIDI CC/NRPN parameter control, global parameters (master tune, transpose), MultiMode, the pitch/mod wheel calibration, the second audio output.
- Envelope time units and stages, glide, LFO table: see FIRMWARE.md section 5-6.

## Skin previews without Docker (2026-10-07)
Needs Pillow and Playwright 1.56 with its Chromium (`pip install pillow playwright==1.56.0`; on an OS Playwright does not know, set
`PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64`, and unpack `libnspr4 libnss3 libasound2t64` with `apt-get download` + `dpkg -x` and point
`LD_LIBRARY_PATH` at them if sudo is not available). From `vst/`: `SHADOW_ART=../../mpc-vst-plugins/tools/html_art.py python3 ../../mpc-vst-plugins/tools/gen_vst.py vst.json`,
then `python3 ../../mpc-vst-plugins/tools/studio.py preview "build/skin/sd88me - VST - Profit-08/Plugin Skins" -o page_%d.png`.
- Release 0.1.1 (2026-10-09): cutoff, resonance, audio mod and volume knobs smoothed (no zipper steps); knobs redrawn as the hardware's (ribbed black skirt, thin silver ring, black brushed top, white pointer) with the orange value arc; BANKS steppers inset from the cheeks. Installed on the Force; bench p99 34.2 %, max 36.3 %, WARN as before. Rebuilt afterwards with the internal version number at 1001.
- Release 0.1.2 (prepared 2026-10-14, not yet built): same source as 0.1.1, internal version number 1002, first stable release with an aarch64 zip. Notes in `docs/release-notes-0.1.2.md`. Before tagging: build both zips with `release.py --version 0.1.2 --id profit-08 --repo sd88me/mpc-vst-profit8 --license MIT --user-data Preset_Banks` (once per target), `catalog_check.py --catalog` OK, attach both to one `profit-08-v0.1.2` release, delete the `profit-08-v0.1.1-gen2-test` pre-release, and set `tested.json`'s Gen2 entry to 0.1.2 only if the shipped aarch64 build is the one the tester ran. The Gen2 test so far (2026-10-14, MPC Live III, MPC OS 3.9.1) was on the 0.1.1 Gen2 test build.
