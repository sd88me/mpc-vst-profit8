#pragma once
/* Curves fitted to the Prophet '08 firmware tables (docs/FIRMWARE.md) or, where marked estimate, to the manual only. */
float p8_note_hz(float semis);       /* semitones above 8.176 Hz (MIDI note 0) */
float p8_lpf_hz(float semis);        /* filter cutoff for the 0-164 parameter: C0 = 16.35 Hz at 0, "more than 13 octaves" */
float p8_lfo_hz(int v);              /* 0-150 unsynced */
float p8_env_seconds(float v);       /* envelope time parameter 0-127: the voice CPU's table (unit assumed to be ms) */
float p8_glide_octave_seconds(float v);   /* estimate */
