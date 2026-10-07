/* Offline engine test: gcc -O2 -fsanitize=address,undefined -Isrc -Ianalog -I../mpc-vst-plugins/wrapper test/test_engine.c src/engine.c src/curves.c src/syx.c -lm
 * usage: test_engine [DIR]   DIR holds "Preset Banks" (default: ./testdata); every program of every bank is played. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "engine.h"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { printf("FAIL " __VA_ARGS__); printf("\n"); fails++; } else { printf("ok   " __VA_ARGS__); printf("\n"); } } while (0)

static float render(const mpc_engine_t *e, void *h, int blocks, float *peak, double *rms) {
    int16_t buf[256];
    double sum = 0; float pk = 0; int bad = 0;
    for (int b = 0; b < blocks; b++) {
        e->render(h, buf, 128);
        for (int i = 0; i < 256; i++) { float x = buf[i] / 32768.0f; sum += x * x; if (fabsf(x) > pk) pk = fabsf(x); }
    }
    if (peak) *peak = pk;
    if (rms) *rms = sqrt(sum / (blocks * 256.0));
    return bad;
}
/* strongest partial of the mixed output between 60 Hz and 12 kHz (Goertzel scan, quarter-semitone steps) over `blocks` blocks */
static float peak_freq(const mpc_engine_t *e, void *h, int blocks) {
    int n = blocks * 128;
    float *x = malloc(sizeof(float) * (size_t)n);
    int16_t buf[256];
    for (int b = 0; b < blocks; b++) { e->render(h, buf, 128); for (int i = 0; i < 128; i++) x[b * 128 + i] = (buf[2 * i] + buf[2 * i + 1]) * (1.0f / 65536); }
    double best = 0, bf = 0;
    for (double f = 60; f < 12000; f *= 1.0145) {
        double w = 2 * M_PI * f / 44100, c = 2 * cos(w), s1 = 0, s2 = 0;
        for (int i = 0; i < n; i++) { double s0 = x[i] * (0.5 - 0.5 * cos(2 * M_PI * i / n)) + c * s1 - s2; s2 = s1; s1 = s0; }
        double p = s1 * s1 + s2 * s2 - c * s1 * s2;
        if (p > best) { best = p; bf = f; }
    }
    free(x);
    return (float)bf;
}
static float freq_of(const mpc_engine_t *e, void *h, int blocks) { return peak_freq(e, h, blocks); }

int main(int argc, char **argv) {
    const char *dir = argc > 1 ? argv[1] : "testdata";
    const mpc_engine_t *e = mpc_engine();
    void *h = e->create(dir);
    char b[64];
    e->get_param(h, "status", b, sizeof b);
    printf("status: %s\n", b);
    e->set_param(h, "bank", "0"); e->set_param(h, "program", "0");
    uint8_t on[3] = {0x90, 60, 100}, off[3] = {0x80, 60, 0};
    /* 1: pitch of the Basic Patch, default osc2 detune aside: make a clean single saw */
    e->set_param(h, "osc2_shape", "0"); e->set_param(h, "osc_mix", "0"); e->set_param(h, "lpf_freq", "164");
    e->set_param(h, "aenv_s", "127"); e->set_param(h, "vca_env", "127"); e->set_param(h, "osc1_fine", "50"); e->set_param(h, "slop", "0");
    e->midi(h, on, 3);
    render(e, h, 40, NULL, NULL);
    float f = freq_of(e, h, 200);
    CHECK(fabsf(f - 261.63f) < 2.0f, "note 60 plays %.2f Hz (want 261.63)", f);
    e->midi(h, off, 3);
    render(e, h, 1000, NULL, NULL);
    double r; float pk;
    render(e, h, 20, &pk, &r);
    CHECK(r < 1e-4, "silent after release (rms %.6f)", r);
    /* 2: 4-pole filter self-oscillation: no oscillators, resonance up, a note: a tone near the cutoff */
    e->set_param(h, "osc1_shape", "0"); e->set_param(h, "noise", "40"); e->set_param(h, "lpf_res", "127"); e->set_param(h, "lpf_freq", "72");
    e->set_param(h, "lpf_key", "0");
    e->midi(h, on, 3);
    render(e, h, 400, NULL, NULL);
    f = freq_of(e, h, 400);
    float want = 16.3516f * powf(2, 72 / 12.0f);
    CHECK(fabsf(12 * log2f(f / want)) < 1.0f, "self-oscillation at %.1f Hz for cutoff %.1f Hz (%.2f semitones off)", f, want, 12 * log2f(f / want));
    e->midi(h, off, 3);
    e->set_param(h, "lpf_res", "0");
    /* 3: every program of every bank */
    int nb = 0, silent = 0, loud = 0, progs = 0;
    for (int bank = 0; bank < 64; bank++) {
        char v[16];
        snprintf(v, sizeof v, "%d", bank);
        e->set_param(h, "bank", v);
        e->get_param(h, "bank", b, sizeof b);
        if (atoi(b) != bank) break;
        nb++;
        for (int p = 0; p < 128; p++) {
            snprintf(v, sizeof v, "%d", p);
            e->set_param(h, "program", v);
            uint8_t chord[4][3] = {{0x90, 48, 100}, {0x90, 55, 100}, {0x90, 64, 100}, {0x90, 72, 100}};
            for (int k = 0; k < 4; k++) e->midi(h, chord[k], 3);
            int16_t buf[256]; float p2 = 0; int nan = 0;
            for (int blk = 0; blk < 300; blk++) { e->render(h, buf, 128); for (int i = 0; i < 256; i++) { float x = buf[i] / 32768.0f; if (fabsf(x) > p2) p2 = fabsf(x); } }
            (void)nan;
            if (p2 < 0.001f) { silent++; e->get_param(h, "patch_name", b, sizeof b); printf("  silent: bank %d %s\n", bank, b); }
            if (p2 > 0.999f) loud++;
            progs++;
            e->midi(h, (uint8_t[]){0xB0, 123, 0}, 3);
            for (int blk = 0; blk < 30; blk++) e->render(h, buf, 128);
        }
    }
    printf("%d banks, %d programs rendered: %d silent, %d clipping\n", nb, progs, silent, loud);
    CHECK(progs >= 128, "banks load (%d programs)", progs);
    CHECK(silent * 10 < progs, "fewer than 10%% silent (%d of %d)", silent, progs);
    e->destroy(h);
    printf(fails ? "FAILED\n" : "PASSED\n");
    return fails != 0;
}
