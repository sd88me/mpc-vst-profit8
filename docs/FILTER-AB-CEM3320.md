# Filter A/B: Profit-08's filter against the Profit-5 CEM 3320 model

Offline experiment, 2026-11-24. **Nothing in Profit-08 was changed.** Profit-08's own engine was copied to a scratch folder and run twice on the
same programs and notes. Nothing here was checked against a real Prophet '08, and no ROM, firmware or recording is committed.

## Question
Profit-08's 4-pole lowpass is `ma_ota_lpf` (a general OTA-ladder model in the shared `mpc_analog.h`). Profit-5 (3.0.0, 2026-11) models the CEM 3320
filter section as a circuit (`ma_vcf3320`, merged into the shared header in Morpho-PE on 2026-11-24). Would that sound closer for the '08?

## What is known about the '08's filter
Nothing that a circuit model could use. No schematic or service manual for the Prophet '08, Evolver or Mopho was found. Sequential calls the filter
"Curtis" (the DSM01 module page says so for the Evolver, Mopho, Prophet-08 and Prophet 12). An Amazona review of the DSM01 (2014) says its chip is the
"DSI-120", "a modern version of the CEM3320" and the same one as in many DSI synths, but a reader comment disputes that and the review gives no source.
The Prophet-5 model's resistor network, coupling and resonance VCA are the Prophet-5 Rev 3 values, so this tests a model, not the instrument.

## Method
- **A**: Profit-08's filter as it is. **B**: `ma_vcf3320` in its place for 4-pole programs (2-pole programs have no 3320 equivalent and were left alone).
- B's cutoff trimmed x1.0175 (it rang 0.3 semitone flat at every cutoff); resonance mapped so the small-signal loop gain equals A's (`4.6 x res`);
  the Prophet-5 model's Q compensation on the output's bass at exponent 0.5 (0 and 1.0 were also run).
- One finding on the way: A's cutoff table reaches 48 semitones below C0, so B's cutoff clamp had to allow it too (a clamp at C0 cost patches with a very low cutoff 6 dB).
- Input: noise only (responses), then all 228 four-pole programs in the three banks of `testdata/Preset_Banks`, three held notes (C2 G2 C3, 2.5 s, then released).
- Brightness is the spectral centroid of the sustained part. Level is RMS of the whole render.

## Results
Noise through the filter at a 2.1 kHz cutoff (peak over the bass, dB):

| | RES 0 | RES 40 | RES 90 | RES 105 | RES 118 |
|---|---|---|---|---|---|
| A | +1.6 | +5.8 | +19.0 | +27.2 | +37.4 |
| B | +1.5 | +6.1 | +20.3 | +31.2 | +41.8 |

- Self-oscillation: both ring in tune once trimmed. B rings at about half A's level.
- Roll-off at 1, 2, 4 and 8 kHz agrees within about 1 dB at low resonance.
- 228 programs, B against A: median level -0.7 dB (10th to 90th percentile -5.5 to +1.0), 73% within 3 dB and 89% within 6 dB; brightness median -3%
  (10th to 90th percentile -21% to +11%). Without Q compensation B is 2.5 dB quieter at the median; with exponent 1.0 it is 0.3 dB louder and 8% darker.
- Programs with no resonance match almost exactly (Fusion Bass, Box o' Morons, Homeorgan, P5 OctaveSaw: level within 0.1 dB, brightness within 1%).
- **Where B differs a lot:** programs with a cutoff under about 30 Hz and heavy filter audio-mod (Lost In Thought, P5 FilterMod, P5 ElecPiano) come out
  13 to 18 dB quieter and 70 to 400% brighter. The 3320 kernel was not checked in that region.

## What this does and does not show
- In the small-signal sense the two filters are close. The differences are in the nonlinear behaviour: B rings lower and peaks higher at high resonance.
- Nothing here says which is closer to a real '08. That needs the instrument, a service manual, or the DSI-120's datasheet.
- No change is proposed. If B is wanted, the route is the one Profit-5 used: a new model version of the engine, so saved sounds keep their sound.

## Reproducing
The harness is two files (`ab.c`, and a patch to a copy of `src/engine.c` that adds the B path behind a flag), kept outside the repo in the author's `~/profit08-ab/harness/`.
A listening page with ten of the programs (A, B, a blind mode and loudness matching) was published as a private Claude artifact; the programs are Profit-08's
own banks, rendered offline.
