#include <math.h>
#include "curves.h"

float p8_note_hz(float s) { return 8.1757989f * exp2f(s * (1.0f / 12)); }
float p8_lpf_hz(float v) { return 16.351598f * exp2f(v * (1.0f / 12)); }

/* Unsynced LFO. The firmware's frequency table is not in the voice CPU or main CPU image (the LFOs run in the voice CPU as a phase
 * increment per tick, not found yet): this is the Poly Evolver's scale, which the manual's text matches (slow = 30 s at 0, 8 Hz = C-2
 * at 90, semitone steps to 261 Hz = middle C at 150): round decimal frequencies up to 89 (piecewise linear), then semitones. */
float p8_lfo_hz(int v) {
    static const float bp[][2] = {{0, 0.0333f}, {1, 0.04f}, {13, 0.16f}, {14, 0.18f}, {15, 0.2f}, {16, 0.23f}, {17, 0.26f}, {18, 0.3f},
        {19, 0.35f}, {20, 0.4f}, {30, 0.9f}, {31, 1.0f}, {38, 1.35f}, {39, 1.45f}, {42, 1.6f}, {43, 1.7f}, {46, 2.0f}, {76, 5.0f},
        {86, 7.0f}, {87, 7.3f}, {88, 7.6f}, {89, 7.7f}};
    if (v >= 90) return 8.1757989f * exp2f((v - 90) * (1.0f / 12));
    int n = sizeof bp / sizeof bp[0];
    for (int i = 1; i < n; i++)
        if (v <= bp[i][0]) return bp[i - 1][1] + (v - bp[i - 1][0]) * (bp[i][1] - bp[i - 1][1]) / (bp[i][0] - bp[i - 1][0]);
    return bp[n - 1][1];
}

/* The voice CPU's 128-entry time table (0x06EC): 10 a step to 500 at index 50, then 700 at 55, 1000 at 60, 1700 at 67, 2400 at 73,
 * 3100 at 80 (about 200 a step), 10 700 at 117 and 14 500 at 127 (breakpoints within 2 %). The unit is not in the file; read as ms. */
float p8_env_seconds(float v) {
    static const float bp[][2] = {{0, 0}, {50, 500}, {55, 700}, {60, 1000}, {67, 1700}, {68, 1900}, {73, 2400}, {74, 2400}, {76, 2700},
        {80, 3100}, {117, 10700}, {127, 14500}};
    if (v <= 0) return 0;
    int n = sizeof bp / sizeof bp[0];
    for (int i = 1; i < n; i++)
        if (v <= bp[i][0]) return (bp[i - 1][1] + (v - bp[i - 1][0]) * (bp[i][1] - bp[i - 1][1]) / (bp[i][0] - bp[i - 1][0])) * 0.001f;
    return 14.5f;
}

/* Glide: seconds per octave, 3 ms at 1 to 6 s at 127 (an estimate: the glide code was not traced). */
float p8_glide_octave_seconds(float v) { return v <= 0 ? 0 : 0.003f * powf(2000.0f, v * (1.0f / 127)); }
