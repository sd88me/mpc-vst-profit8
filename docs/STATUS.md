# Status (2026-10-07)

## Done (offline)
- Firmware tools (`tools/fw/p8_fw.py`), program layout table (`tools/gen_patch.py`, checked against 512 programs), 347 VST parameters.
- Engine (`src/engine.c`): 8 voices, two layers with normal / stack / split keyboard modes, poly and unison (1 voice, all voices, three detune sets from the
  firmware), per-oscillator glide, sync 2 > 1, analog oscillators (saw, triangle, saw-tri, pulse 0-99 off at the extremes), 2/4-pole OTA lowpass with envelope,
  velocity, key, audio mod, VCA, pan spread, three DADSR envelopes, four LFOs, four mod slots, the five controller routes, the 4 x 16 gated sequencer with all
  trigger modes, the arpeggiator (five patterns, 1-3 octaves), the bank loader (Preset Banks folder).
- Analog section (shared `analog/mpc_analog.h`): Eco 1x or High 2x (Quality). The filter's self-oscillation tuning compensation from the shared header is applied in both:
  self-oscillation lands within 0.15 semitone of the set cutoff at 1 kHz (test_engine).
- Tests: `test/test_engine.c` (pitch, self-oscillation, silence after release, all 640 programs of the three banks: none clip, 2 silent) and
  `tools/test_port.sh vst/vst.json` (all pass but the known wheel-click rounding on a 0-120 range, as Morpho-PE).

## Not done
- The skin and Q-Link pages (an auto-layout only), the device build and bench, state/bank handling on a device.
- Drone (VCA level above 0 with no key held) is not modelled: a voice sounds only while gated or releasing.
- MIDI CC/NRPN parameter control, global parameters (master tune, transpose), MultiMode, the pitch/mod wheel calibration, the second audio output.
- Envelope time units and stages, glide, LFO table: see FIRMWARE.md section 5-6.
