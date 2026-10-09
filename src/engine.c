/* Profit-08: an eight-voice instrument modelled on the Prophet '08 (manual v1.3, Main OS 2.3 and Voice OS 1.5 tables).
 * The program is the instrument's own 384 bytes (layers A and B, 4 x 16 sequencer steps each, the name), so its SysEx dumps load as they are.
 *
 * One voice = two band-limited ramp-core oscillators (hard sync 2 > 1) -> mixer + noise -> a 2/4-pole OTA-cascade lowpass -> VCA -> pan.
 * Modulation (three envelopes, four LFOs, four mod slots, the controller routes, a 4 x 16 gated sequencer and an arpeggiator per layer) is
 * computed every CTL samples. Keyboard modes: normal (8 voices, layer A), stack (A and B on every note, 4 voices each) and split. */
#include <dirent.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include "engine.h"
#include "mpc_analog.h"
#include "patch_tab.h"
#include "curves.h"
#include "syx.h"

#ifndef P8_DEFAULT_OS
#define P8_DEFAULT_OS 1     /* Eco: the analog section at 1x; the Quality parameter switches to 2x */
#endif
#ifndef P8_MASTER
#define P8_MASTER 1.27f     /* 2 dB below the first fix: single note peaks about 0.28 on the factory programs (docs/STATUS.md) */
#endif
#define FS 44100.0f
#define MAXV 8
#define CTL 16
#define DT (CTL / FS)
#define MAXBANKS 64
#define PATHLEN 512
#define BANKDIR "Preset_Banks"      /* no space: the release installer keeps this folder across upgrades and does not accept spaces */
#define BANKDIR_ALT "Preset Banks"  /* also scanned */

/* Depth of each destination at full source and amount: the destination's own parameter range (docs/FIRMWARE.md section 9: an
 * assumption that matches the filter, whose envelope amount of +127 sweeps its whole 0-164 range in the factory programs). */
static const float RANGE[44] = {0, 120, 120, 120, 127, 127, 99, 99, 99, 164, 127, 127, 127, 127, 150, 150, 150, 150, 150, 127, 127, 127, 127,
    127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127};
/* cycles per sequencer step for the synced LFO settings 151-166 (manual p. 16): 32 steps a cycle ... 16 cycles a step */
static const float SYNC_CPS[16] = {1.0f / 32, 1.0f / 16, 1.0f / 8, 1.0f / 6, 1.0f / 4, 1.0f / 3, 1.0f / 2, 2.0f / 3, 1, 1.5f, 2, 3, 4, 6, 8, 16};
static const char *const SYNC_NAMES[16] = {"32 Steps", "16 Steps", "8 Steps", "6 Steps", "4 Steps", "3 Steps", "2 Steps", "1.5 Step", "1 Step",
    "2/3 Step", "1/2 Step", "1/3 Step", "1/4 Step", "1/6 Step", "1/8 Step", "1/16 Step"};
/* steps per beat for each clock divide and the swing (fraction of a step the odd steps are delayed by) */
static const float DIV_MULT[13] = {0.5f, 1, 2, 2, 2, 3, 4, 4, 4, 6, 8, 12, 24};
static const float DIV_SWING[13] = {0, 0, 0, 1.0f / 6, 1.0f / 3, 0, 0, 1.0f / 6, 1.0f / 3, 0, 0, 0, 0};
/* Unison detune in cents for voices 1-8 in the three detune modes: the main CPU's table (main 0x0D5E, docs/FIRMWARE.md section 4) */
static const signed char DETUNE[3][8] = {{-1, 1, 2, -2, -3, 3, 4, -4}, {2, -2, 4, -4, -6, 6, -8, 8}, {-3, 3, -6, 6, -9, 9, -12, 12}};
static const float PAN_POS[8] = {-1, 1, -0.5f, 0.5f, -0.75f, 0.75f, -0.25f, 0.25f};

enum { ST_IDLE, ST_DELAY, ST_ATT, ST_DEC, ST_SUS, ST_REL };
typedef struct { int st; float lvl, t; } env_t;
typedef struct { float ph, val; } lfo_t;
typedef struct {
    int on, layer, note, gate, sgate;
    unsigned age;
    float vel;
    float cur[2];                       /* glided pitch of each oscillator, MIDI note units, before fine tune and modulation */
    float ph[2], sync_corr;
    float lad[4], ladd[4];
    ma_hb_t dec;
    env_t env[3];
    lfo_t lfo[4];
    float slop[2], slop_t[2];
    float acc[44];
    uint32_t rng;
    /* control-rate results */
    int shape[2];
    float scut, sres; int sm_init;   /* knob values smoothed against zipper steps */
    float inc[2], duty[2], mix, noise, cut, cut_prev, res, am, vca, vca_prev, panl, panr, vol, gains;
    int four;
} voice_t;

typedef struct {
    int held[16], nheld;                /* key stack, last at the top */
    int uni_note;                       /* note the unison voices play, -1 none */
    float wait;                         /* steps until the next clock step */
    int parity, step, running, arp_idx, arp_dir, arp_note;
    float arp_gate;
    float sval[4];                      /* the sequencer's current step values, 0-125 */
    int sp;                             /* sequencer position the values were read at */
} layer_t;

typedef struct { char name[40]; uint8_t (*prog)[NPROGBYTES]; } bank_t;

typedef struct {
    uint8_t patch[NPATCH];
    voice_t v[MAXV];
    layer_t ly[2];
    bank_t banks[MAXBANKS];
    int nbanks, cur_bank, cur_prog, os, layer_sel, browse_bank, browse_page;
    char dir[PATHLEN], status[96];
    unsigned age, display_rev;
    float bend, t_wheel, t_press, t_breath, t_foot, t_expr, wheel, press, breath, foot, expr, cc_vol;
    int pedal, clock_src, seq_run, transport;
    uint8_t deferred[128], layer_mask[128];
    float host_bpm;
    uint32_t rng;
    uint8_t rrv;
} p8_t;

static ma_hb_t dummy_hb;
static float HB_A[MA_HB_A_M], HB_B[MA_HB_B_M];
static float G_TAB[2][4096], ENV_S[1290], LFO_HZ[167], PAN_C[129], PAN_S[129];

static inline float clampf(float x, float lo, float hi) { return x < lo ? lo : x > hi ? hi : x; }
static inline int clampi(int x, int lo, int hi) { return x < lo ? lo : x > hi ? hi : x; }
static float rnd(uint32_t *r) { *r = *r * 1664525u + 1013904223u; return (int32_t)*r * (1.0f / 2147483648.0f); }

static void init_tables(void) {
    static int done;
    if (done) return;
    for (int i = 0; i < 4096; i++) {
        float f = p8_lpf_hz(i / 16.0f - 48);
        if (f > 0.45f * FS) f = 0.45f * FS;
        for (int q = 0; q < 2; q++) { float gq = tanf(3.14159265f * f / (FS * (1 << q))); G_TAB[q][i] = gq / (1 + gq); }
    }
    ma_hb_design_standard(HB_A, HB_B);
    (void)dummy_hb;
    for (int i = 0; i < 1290; i++) ENV_S[i] = p8_env_seconds(i * 0.1f);
    for (int i = 0; i <= 166; i++) LFO_HZ[i] = i > 150 ? 0 : p8_lfo_hz(i);
    for (int i = 0; i <= 128; i++) { float a = i * (1.0f / 128) * 1.5707963f; PAN_C[i] = cosf(a); PAN_S[i] = sinf(a); }
    done = 1;
}
static inline float env_s(float v) {
    float x = v * 10;
    if (x <= 0) return 0;
    if (x >= 1269) return ENV_S[1270];
    int i = (int)x;
    return ENV_S[i] + (x - i) * (ENV_S[i + 1] - ENV_S[i]);
}
static float lpf_G(int q, float semis) {
    const float *T = G_TAB[q];
    float x = (semis + 48) * 16;
    if (x <= 0) return T[0];
    if (x >= 4094) return T[4094];
    int i = (int)x;
    return T[i] + (x - i) * (T[i + 1] - T[i]);
}

/* ---------------- patch access ---------------- */
#define LP(s, l, i) ((s)->patch[(l) * B_OFF + (i)])

static void basic_patch(uint8_t *p) {
    for (int i = 0; i < NPATCH; i++) p[i] = (uint8_t)PTAB[i].def;
    memset(p + NAME_AT, ' ', 16);
    memcpy(p + NAME_AT, "Basic Patch", 11);
}
static void patch_clamp(uint8_t *p) {
    for (int i = 0; i < NPATCH; i++) if (PTAB[i].key[0] && p[i] > PTAB[i].max) p[i] = (uint8_t)PTAB[i].max;
}

#define BANK_SLOTS 11
#define PROG_SLOTS 45
#define PROG_PAGES ((128 + PROG_SLOTS - 1) / PROG_SLOTS)
/* ---------------- banks ---------------- */
typedef struct { p8_t *s; const char *base; int bi[2]; int nb; } scan_ctx;
static int new_bank(p8_t *s, const char *name) {
    if (s->nbanks >= MAXBANKS) return -1;
    bank_t *b = &s->banks[s->nbanks];
    b->prog = malloc(128 * NPROGBYTES);
    if (!b->prog) return -1;
    for (int i = 0; i < 128; i++) basic_patch(b->prog[i]);
    snprintf(b->name, sizeof b->name, "%s", name);
    return s->nbanks++;
}
static void scan_cb(void *ctx, int bank, int num, const uint8_t *prog) {
    scan_ctx *c = ctx;
    if (bank < 0) return;
    if (c->bi[bank] < 0) {
        char nm[64];
        snprintf(nm, sizeof nm, "%.34s", c->base);
        if (c->bi[bank ^ 1] >= 0) {
            char *n1 = c->s->banks[c->bi[bank ^ 1]].name;
            if (strlen(n1) < sizeof(c->s->banks[0].name) - 3 && !strstr(n1, " 1")) strcat(n1, bank ? " 1" : " 2");
            snprintf(nm, sizeof nm, "%.30s %d", c->base, bank + 1);
        }
        c->bi[bank] = new_bank(c->s, nm);
        if (c->bi[bank] < 0) return;
    }
    memcpy(c->s->banks[c->bi[bank]].prog[num], prog, NPROGBYTES);
    patch_clamp(c->s->banks[c->bi[bank]].prog[num]);
}
static int cmpstr(const void *a, const void *b) { return strcasecmp(*(char *const *)a, *(char *const *)b); }
static void scan_dir(p8_t *s, const char *dir) {
    DIR *d = opendir(dir);
    if (!d) return;
    char *names[256];
    int n = 0;
    struct dirent *e;
    while ((e = readdir(d)) && n < 256) {
        size_t l = strlen(e->d_name);
        if (l > 4 && !strcasecmp(e->d_name + l - 4, ".syx") && e->d_name[0] != '.') names[n++] = strdup(e->d_name);
    }
    closedir(d);
    qsort(names, (size_t)n, sizeof *names, cmpstr);
    for (int i = 0; i < n; i++) {
        char path[PATHLEN];
        snprintf(path, sizeof path, "%s/%s", dir, names[i]);
        FILE *f = fopen(path, "rb");
        if (f) {
            fseek(f, 0, SEEK_END);
            long sz = ftell(f);
            fseek(f, 0, SEEK_SET);
            if (sz > 0 && sz < (8 << 20)) {
                uint8_t *buf = malloc((size_t)sz);
                if (buf && fread(buf, 1, (size_t)sz, f) == (size_t)sz) {
                    char base[64];
                    snprintf(base, sizeof base, "%s", names[i]);
                    base[strlen(base) - 4] = 0;
                    scan_ctx c = {s, base, {-1, -1}, 0};
                    syx_each_program(buf, (size_t)sz, scan_cb, &c);
                }
                free(buf);
            }
            fclose(f);
        }
        free(names[i]);
    }
}

/* ---------------- voices ---------------- */
static void layer_range(const p8_t *s, int l, int *lo, int *hi) {
    if (LP(s, 0, 0) >= 0 && s->patch[P_KBD_MODE] == 0) { *lo = 0; *hi = MAXV; }
    else { *lo = l ? 4 : 0; *hi = l ? MAXV : 4; }
}
static int kbd_mode(const p8_t *s) { return s->patch[P_KBD_MODE]; }

static void voice_trigger(voice_t *v) {
    for (int e = 0; e < 3; e++) { v->env[e].st = ST_DELAY; v->env[e].t = 0; }
    for (int i = 0; i < 4; i++) if (0) v->lfo[i].ph = 0;
}
static void voice_release(voice_t *v) {
    for (int e = 0; e < 3; e++) if (v->env[e].st != ST_IDLE) v->env[e].st = ST_REL;
}
static void voice_start(p8_t *s, voice_t *v, int l, int note, float vel, int trig, int vi) {
    const uint8_t *p = &LP(s, l, 0);
    int fresh = !v->on || (v->env[1].st == ST_IDLE);
    v->layer = l;
    v->on = 1;
    v->note = note;
    v->vel = vel;
    v->age = ++s->age;
    v->gate = 1;
    v->sgate = 1;
    for (int o = 0; o < 2; o++) {
        float tgt = (float)note;
        if (fresh) v->cur[o] = tgt;
        (void)p;
    }
    for (int i = 0; i < 4; i++) {
        const uint8_t *q = p + P_LFO1_FREQ + 5 * i;
        if (q[4]) { v->lfo[i].ph = 0; }
    }
    (void)vi;
    if (trig) voice_trigger(v);
}

static voice_t *alloc_voice(p8_t *s, int lo, int hi) {
    voice_t *best = NULL;
    for (int i = lo; i < hi; i++) if (!s->v[i].on) return &s->v[i];
    unsigned bage = 0xFFFFFFFFu;
    for (int i = lo; i < hi; i++)
        if (!s->v[i].gate && s->v[i].age < bage) { bage = s->v[i].age; best = &s->v[i]; }
    if (best) return best;
    bage = 0xFFFFFFFFu;
    for (int i = lo; i < hi; i++) if (s->v[i].age < bage) { bage = s->v[i].age; best = &s->v[i]; }
    return best;
}

static int is_unison(const p8_t *s, int l) { return LP(s, l, P_UNISON) != 0; }

/* start a note on a layer's voices (poly: one voice; unison: the 1-voice mode or every voice of the layer) */
static void play_note(p8_t *s, int l, int note, float vel, int retrig) {
    int lo, hi;
    layer_range(s, l, &lo, &hi);
    if (is_unison(s, l)) {
        int cnt = LP(s, l, P_UNISON_MODE) == 0 ? 1 : hi - lo;
        int legato = s->ly[l].uni_note >= 0 && s->v[lo].gate;
        for (int i = lo; i < lo + cnt; i++) {
            voice_t *v = &s->v[i];
            int fresh = !v->on;
            voice_start(s, v, l, note, vel, !legato || retrig, i);
            if (fresh) v->cur[0] = v->cur[1] = (float)note;
        }
        for (int i = lo + cnt; i < hi; i++) if (s->v[i].gate) { s->v[i].gate = 0; voice_release(&s->v[i]); }
        s->ly[l].uni_note = note;
        return;
    }
    voice_t *v = alloc_voice(s, lo, hi);
    if (!v) return;
    int fresh = !v->on || v->env[1].st == ST_IDLE;
    voice_start(s, v, l, note, vel, 1, (int)(v - s->v));
    if (fresh) v->cur[0] = v->cur[1] = (float)note;
}
static void stop_note(p8_t *s, int l, int note) {
    int lo, hi;
    layer_range(s, l, &lo, &hi);
    if (is_unison(s, l)) {
        if (s->ly[l].uni_note != note) return;
        for (int i = lo; i < hi; i++) if (s->v[i].gate) { s->v[i].gate = 0; voice_release(&s->v[i]); }
        s->ly[l].uni_note = -1;
        return;
    }
    for (int i = lo; i < hi; i++) if (s->v[i].gate && s->v[i].note == note && s->v[i].layer == l) { s->v[i].gate = 0; voice_release(&s->v[i]); }
}

static int priority_note(const p8_t *s, int l) {
    const layer_t *y = &s->ly[l];
    int mode = LP(s, l, P_KEY_MODE) >> 1, best = y->held[y->nheld - 1];
    if (mode == 0) { for (int i = 0; i < y->nheld; i++) if (y->held[i] < best) best = y->held[i]; }
    else if (mode == 1) { for (int i = 0; i < y->nheld; i++) if (y->held[i] > best) best = y->held[i]; }
    return best;
}

static void ly_reset_seq(p8_t *s, int l) { layer_t *y = &s->ly[l]; y->step = 0; y->parity = 0; y->wait = 0; (void)s; }

static void layer_note_on(p8_t *s, int l, int note, float vel) {
    layer_t *y = &s->ly[l];
    int was = y->nheld;
    for (int i = 0; i < y->nheld; i++) if (y->held[i] == note) { memmove(y->held + i, y->held + i + 1, (size_t)(y->nheld - i - 1) * sizeof(int)); y->nheld--; break; }
    if (y->nheld < 16) y->held[y->nheld++] = note;
    int arp = LP(s, l, P_ARP), gseq = LP(s, l, P_GSEQ), trig = LP(s, l, P_SEQ_TRIG);
    if (gseq && (trig == 0 || trig == 2 || !was)) { ly_reset_seq(s, l); y->sp = -1; }
    if (arp) { if (!was) { y->arp_idx = 0; y->arp_dir = 1; y->wait = 0; y->parity = 0; } s->v[0].vel = vel; y->arp_gate = 0; return; }
    if (is_unison(s, l)) {
        int want = priority_note(s, l);
        int retrig = LP(s, l, P_KEY_MODE) & 1;
        if (want == note || y->uni_note < 0) play_note(s, l, want, vel, retrig || y->uni_note < 0);
    } else play_note(s, l, note, vel, 1);
}
static void layer_note_off(p8_t *s, int l, int note) {
    layer_t *y = &s->ly[l];
    int found = 0;
    for (int i = 0; i < y->nheld; i++) if (y->held[i] == note) { memmove(y->held + i, y->held + i + 1, (size_t)(y->nheld - i - 1) * sizeof(int)); y->nheld--; found = 1; break; }
    if (!found) return;
    if (LP(s, l, P_ARP)) { if (!y->nheld && y->arp_note >= 0) { stop_note(s, l, y->arp_note); y->arp_note = -1; } return; }
    if (is_unison(s, l)) {
        if (y->nheld && y->uni_note == note) { int want = priority_note(s, l); play_note(s, l, want, 0.8f, LP(s, l, P_KEY_MODE) & 1); }
        else if (!y->nheld) stop_note(s, l, y->uni_note);
    } else stop_note(s, l, note);
}

static void note_on(p8_t *s, int note, int vel) {
    int km = kbd_mode(s), mask = 1;
    if (km == 1) mask = 3;
    else if (km == 2) mask = note < s->patch[P_SPLIT_POINT] ? 1 : 2;
    s->layer_mask[note] = (uint8_t)mask;
    for (int l = 0; l < 2; l++) if (mask >> l & 1) layer_note_on(s, l, note, vel / 127.0f);
}
static void note_off(p8_t *s, int note) {
    if (s->pedal) { s->deferred[note] = 1; return; }
    int mask = s->layer_mask[note] ? s->layer_mask[note] : 1;
    for (int l = 0; l < 2; l++) if (mask >> l & 1) layer_note_off(s, l, note);
    s->layer_mask[note] = 0;
}
static void all_off(p8_t *s) {
    for (int i = 0; i < MAXV; i++) { s->v[i].gate = 0; voice_release(&s->v[i]); }
    for (int l = 0; l < 2; l++) { s->ly[l].nheld = 0; s->ly[l].uni_note = -1; s->ly[l].arp_note = -1; }
    memset(s->deferred, 0, sizeof s->deferred);
}

/* ---------------- clock, arpeggiator, gated sequencer ---------------- */
static float steps_per_sec(const p8_t *s, int l) {
    float bpm = (s->clock_src && s->host_bpm > 0) ? s->host_bpm : (float)LP(s, l, P_TEMPO);
    return clampf(bpm, 30, 250) / 60.0f * DIV_MULT[clampi(LP(s, l, P_CLOCK_DIV), 0, 12)];
}

static int cmp_int(const void *a, const void *b) { return *(const int *)a - *(const int *)b; }
static int arp_next(p8_t *s, int l) {
    layer_t *y = &s->ly[l];
    int ap = LP(s, l, P_ARP_MODE), pat = ap % 5, oct = ap / 5 + 1;
    int notes[16 * 3], n = 0;
    int sorted[16];
    memcpy(sorted, y->held, (size_t)y->nheld * sizeof(int));
    if (pat != 3) qsort(sorted, (size_t)y->nheld, sizeof(int), cmp_int);
    if (pat == 3) { for (int o = 0; o < oct; o++) for (int i = 0; i < y->nheld; i++) notes[n++] = sorted[i] + 12 * o; }
    else for (int o = 0; o < oct; o++) for (int i = 0; i < y->nheld; i++) notes[n++] = sorted[i] + 12 * o;
    if (!n) return -1;
    int idx;
    switch (pat) {
    case 0: case 3: idx = y->arp_idx % n; y->arp_idx = (idx + 1) % n; break;
    case 1: idx = n - 1 - (y->arp_idx % n); y->arp_idx = (y->arp_idx + 1) % n; break;
    case 2: {
        int span = n > 1 ? 2 * n - 2 : 1, k = y->arp_idx % span;
        idx = k < n ? k : span - k;
        y->arp_idx = (k + 1) % span;
        break;
    }
    default: idx = (int)((rnd(&s->rng) * 0.5f + 0.5f) * n); if (idx >= n) idx = n - 1; break;
    }
    return clampi(notes[idx], 0, 127);
}

static void do_step(p8_t *s, int l) {
    layer_t *y = &s->ly[l];
    int gseq = LP(s, l, P_GSEQ), arp = LP(s, l, P_ARP);
    if (!y->nheld) return;
    int rest = 0;
    if (gseq) {
        int pos = y->step & 15, reset = 0;
        for (int t = 0; t < 4; t++) if (s->patch[(l ? SEQ_B : SEQ_A) + 16 * t + pos] == 126) reset = 1;
        if (reset && pos != 0) { y->step = 0; pos = 0; }
        for (int t = 0; t < 4; t++) {
            int val = s->patch[(l ? SEQ_B : SEQ_A) + 16 * t + pos];
            y->sval[t] = val >= 126 ? 0.0f : (float)val;
            if (t == 0 && val == 127) rest = 1;
        }
        y->sp = pos;
        y->step = (pos + 1) & 15;
    }
    int lo, hi;
    layer_range(s, l, &lo, &hi);
    if (arp) {
        if (y->arp_note >= 0) { stop_note(s, l, y->arp_note); y->arp_note = -1; }
        int n = arp_next(s, l);
        if (n >= 0 && !rest) { play_note(s, l, n, s->v[0].vel > 0 ? s->v[0].vel : 0.8f, 1); y->arp_note = n; y->arp_gate = 0.5f; }
    } else if (gseq) {
        int trig = LP(s, l, P_SEQ_TRIG);
        for (int i = lo; i < hi; i++) {
            voice_t *v = &s->v[i];
            if (!v->gate || v->layer != l) continue;
            if (rest) { if (v->sgate) { v->sgate = 0; voice_release(v); } }
            else { if (trig == 0 || trig == 1 || !v->sgate) { if (trig <= 1 || !v->sgate) voice_trigger(v); } v->sgate = 1; }
        }
    }
}

static void layer_clock(p8_t *s, int l) {
    layer_t *y = &s->ly[l];
    int arp = LP(s, l, P_ARP), gseq = LP(s, l, P_GSEQ);
    if (!arp && !gseq) {
        for (int t = 0; t < 4; t++) y->sval[t] = 0;
        if (y->arp_note >= 0) { stop_note(s, l, y->arp_note); y->arp_note = -1; }
        return;
    }
    if (!y->nheld) {
        if (y->arp_note >= 0) { stop_note(s, l, y->arp_note); y->arp_note = -1; }
        return;
    }
    if (gseq && LP(s, l, P_SEQ_TRIG) == 4) {   /* key step: the keys advance it (below) */
        if (y->sp < 0) { y->sp = 0; do_step(s, l); }
        return;
    }
    float sps = steps_per_sec(s, l), adv = sps * DT;
    if (y->arp_note >= 0) { y->arp_gate -= adv; if (y->arp_gate <= 0) { stop_note(s, l, y->arp_note); y->arp_note = -1; } }
    y->wait -= adv;
    while (y->wait <= 0) {
        do_step(s, l);
        float sw = DIV_SWING[clampi(LP(s, l, P_CLOCK_DIV), 0, 12)];
        y->parity ^= 1;
        y->wait += y->parity ? 1 + sw : 1 - sw;
    }
}

/* ---------------- control rate ---------------- */
static float lfo_wave(int shape, float ph, float held) {
    switch (shape) {
    case 0: return ph < 0.5f ? 4 * ph - 1 : 3 - 4 * ph;
    case 1: return 1 - 2 * ph;
    case 2: return 2 * ph - 1;
    case 3: return ph < 0.5f ? 1.0f : -1.0f;
    default: return held;
    }
}

static void voice_control(p8_t *s, voice_t *v, int vi) {
    int l = v->layer;
    const uint8_t *p = &LP(s, l, 0);
    layer_t *y = &s->ly[l];
    float src[21] = {0}, acc[44] = {0};
    for (int t = 0; t < 4; t++) src[1 + t] = y->sval[t] * (1.0f / 125);
    for (int i = 0; i < 4; i++) src[5 + i] = v->lfo[i].val;
    for (int e = 0; e < 3; e++) src[9 + e] = v->env[e].lvl;
    src[12] = s->bend; src[13] = s->wheel; src[14] = s->press; src[15] = s->breath; src[16] = s->foot; src[17] = s->expr;
    src[18] = v->vel; src[19] = v->note * (1.0f / 127); src[20] = rnd(&v->rng);
    const float *pa = v->acc;   /* last tick's sums drive the modulation amounts of the mod slots and the LFO / envelope parameters */
    /* LFOs and envelope 3 to their own destinations */
    for (int i = 0; i < 4; i++) {
        const uint8_t *q = p + P_LFO1_FREQ + 5 * i;
        float amt = clampf(q[2] + pa[19 + i] + pa[23], 0, 127) * (1.0f / 127);
        int d = q[3];
        if (d) acc[d] += v->lfo[i].val * amt * RANGE[d];
    }
    {
        int d = p[P_ENV3_DEST];
        float a = (clampf(p[P_ENV3_AMT] - 127 + pa[26] + pa[27], -127, 127)) * (1.0f / 127);
        float vs = 1 - p[P_ENV3_VEL] * (1.0f / 127) * (1 - v->vel);
        if (d) acc[d] += v->env[2].lvl * a * vs * RANGE[d];
    }
    for (int t = 0; t < 4; t++) {
        int d = p[P_SEQ1_DEST + t];
        if (d) acc[d] += y->sval[t] * (RANGE[d] > 127 ? 1.0f : 1.0f);
    }
    for (int m = 0; m < 4; m++) {
        const uint8_t *q = p + P_MOD1_SRC + 3 * m;
        int sidx = q[0], d = q[2];
        if (!sidx || !d) continue;
        float a = clampf(q[1] - 127 + pa[40 + m], -127, 127) * (1.0f / 127);
        acc[d] += src[sidx] * a * RANGE[d];
    }
    static const int CIDX[5] = {P_WHEEL_AMT, P_PRESS_AMT, P_BREATH_AMT, P_VEL_AMT, P_FOOT_AMT};
    static const int CSRC[5] = {13, 14, 15, 18, 16};
    for (int c = 0; c < 5; c++) {
        int d = p[CIDX[c] + 1];
        if (d) acc[d] += src[CSRC[c]] * ((p[CIDX[c]] - 127) * (1.0f / 127)) * RANGE[d];
    }
    memcpy(v->acc, acc, sizeof acc);
    acc[1] += acc[3]; acc[2] += acc[3];
    acc[6] += acc[8]; acc[7] += acc[8];

    /* LFOs */
    float sps = steps_per_sec(s, l);
    for (int i = 0; i < 4; i++) {
        const uint8_t *q = p + P_LFO1_FREQ + 5 * i;
        int fq = clampi((int)lroundf(q[0] + acc[14 + i] + acc[18]), 0, 166);
        float hz = fq > 150 ? SYNC_CPS[fq - 151] * sps : LFO_HZ[fq];
        lfo_t *o = &v->lfo[i];
        o->ph += hz * DT;
        if (o->ph >= 1) { o->ph -= floorf(o->ph); if (q[1] == 4) o->val = rnd(&v->rng); }
        if (q[1] != 4) o->val = lfo_wave(q[1], o->ph, 0);
    }
    /* envelopes */
    float modr[3][3];
    for (int e = 0; e < 3; e++) {
        const uint8_t *q = p + (e == 0 ? P_FENV_DELAY : e == 1 ? P_AENV_DELAY : P_ENV3_DELAY);
        modr[e][0] = clampf(q[1] + acc[28 + e] + acc[31], 0, 127);
        modr[e][1] = clampf(q[2] + acc[32 + e] + acc[35], 0, 127);
        modr[e][2] = clampf(q[4] + acc[36 + e] + acc[39], 0, 127);
        env_t *en = &v->env[e];
        float sus = q[3] * (1.0f / 127);
        int gate = v->gate && v->sgate;
        switch (en->st) {
        case ST_DELAY:
            en->t += DT;
            if (en->t >= env_s(q[0])) { en->st = ST_ATT; en->t = 0; }
            break;
        case ST_ATT: {
            float ta = fmaxf(env_s(modr[e][0]), 0.0008f);
            en->lvl += DT / ta;
            if (en->lvl >= 1) { en->lvl = 1; en->st = ST_DEC; }
            break;
        }
        case ST_DEC: {
            float tau = fmaxf(env_s(modr[e][1]) * (1.0f / 4.6f), 0.0003f);
            { float c = DT / tau; en->lvl += (sus - en->lvl) * (c / (1 + c)); }
            if (fabsf(en->lvl - sus) < 0.002f) {
                en->lvl = sus;
                if (e == 2 && p[P_ENV3_REPEAT] && gate) { en->st = ST_DELAY; en->t = 0; }
                else en->st = ST_SUS;
            }
            break;
        }
        case ST_SUS: en->lvl = sus; break;
        case ST_REL: {
            float tau = fmaxf(env_s(modr[e][2]) * (1.0f / 4.6f), 0.0003f);
            en->lvl /= 1 + DT / tau;
            if (en->lvl < 0.0005f) { en->lvl = 0; en->st = ST_IDLE; }
            break;
        }
        default: break;
        }
        if (!gate && en->st != ST_REL && en->st != ST_IDLE) en->st = ST_REL;
    }
    if (!v->gate && v->env[1].st == ST_IDLE) { v->on = 0; return; }

    /* pitch: glide, fine tune, slop, unison detune, bend, modulation */
    int mode = p[P_GLIDE_MODE];
    int uni = LP(s, l, P_UNISON), umode = p[P_UNISON_MODE];
    float det = 0;
    if (uni && umode >= 2) det = DETUNE[umode - 2][vi] * 0.01f;
    float slop = p[P_SLOP] * 0.015f;
    for (int o = 0; o < 2; o++) {
        const uint8_t *q = p + 5 * o;
        int glide = q[3];
        float tgt = (float)v->note;
        if (glide && !(mode & 1 && !(s->ly[l].nheld > 1))) {
            float d = tgt - v->cur[o];
            float oct = p8_glide_octave_seconds((float)glide);
            float rate = (mode < 2) ? 12.0f / oct : fabsf(d) / fmaxf(env_s(glide) * 0.5f + 0.01f, 0.01f);
            float step = rate * DT;
            v->cur[o] = fabsf(d) <= step ? tgt : v->cur[o] + (d > 0 ? step : -step);
        } else v->cur[o] = tgt;
        if (!(vi & 1) || o == 0) {}
        v->slop_t[o] += DT;
        if (v->slop_t[o] > 0.25f) { v->slop_t[o] = 0; v->slop[o] = rnd(&v->rng) * slop; }
        float semis = (q[4] ? v->cur[o] + (q[0] - 24) : (float)q[0]) + (q[1] - 50) * 0.01f + v->slop[o] + det +
                      s->bend * p[P_BEND_RANGE] + acc[1 + o];
        float hz = p8_note_hz(clampf(semis, 0, 150));
        v->inc[o] = clampf(hz / FS, 1e-5f, 0.45f);
        int sh = q[2];
        v->shape[o] = sh == 0 ? -1 : sh == 1 ? MA_SAW : sh == 2 ? MA_TRI : sh == 3 ? MA_SAWTRI : MA_PULSE;
        v->duty[o] = sh >= 4 ? clampf((sh - 4 + acc[6 + o]) * (1.0f / 99), 0, 1) : 0.5f;
    }
    v->mix = clampf(p[P_OSC_MIX] + acc[4], 0, 127) * (1.0f / 127);
    v->noise = clampf(p[P_NOISE] + acc[5], 0, 127) * (1.0f / 127);
    /* filter: cutoff in semitones from C0 */
    float vs = 1 - p[P_FENV_VEL] * (1.0f / 127) * (1 - v->vel);
    float ea = clampf(p[P_FENV_AMT] - 127 + acc[24] + acc[27], -127, 127) * (1.0f / 127);
    if (!v->sm_init) { v->scut = (float)p[P_LPF_FREQ]; v->sres = (float)p[P_LPF_RES]; v->sm_init = 1; }
    v->scut += ((float)p[P_LPF_FREQ] - v->scut) * 0.03f;
    v->sres += ((float)p[P_LPF_RES] - v->sres) * 0.03f;
    float cut = v->scut + acc[9] + v->env[0].lvl * ea * vs * 164 + (v->note - 60) * p[P_LPF_KEY] * (1.0f / 64);
    v->four = p[P_POLES];
    float res = clampf(v->sres + acc[10], 0, 127) * (1.0f / 127);
    v->res = (v->four ? 4.6f : 1.2f) * res;
    if (v->four && res > 0.4f) {      /* the stages' limiting lowers the self-oscillation pitch: raise the cutoff (analog/mpc_analog.h) */
        float r2 = res * res, hz = p8_lpf_hz(clampf(cut, 0, 164));
        cut += 1.15f * r2 * r2 * fmaxf(0, 1 - sqrtf(fminf(hz, 16000.0f) * (1.0f / 16000)));
    }
    v->cut_prev = v->cut;
    v->cut = clampf(cut, -40, 200);
    v->am = clampf(p[P_LPF_AUDMOD] + acc[11], 0, 127) * (1.0f / 127) * 60.0f;
    /* VCA */
    float vv = 1 - p[P_VCA_VEL] * (1.0f / 127) * (1 - v->vel);
    float lvl = clampf(p[P_VCA_LEVEL] + acc[12], 0, 127) * (1.0f / 127);
    float eamt = clampf(p[P_VCA_ENV] + acc[25] + acc[27], 0, 127) * (1.0f / 127);
    v->vca_prev = v->vca;
    v->vca = clampf(lvl + eamt * vv * v->env[1].lvl, 0, 1);
    float pan = clampf((p[P_SPREAD] + acc[13]) * (1.0f / 127) * PAN_POS[vi], -1, 1);
    float pf = (pan + 1) * 64.0f;
    int pi = (int)pf;
    if (pi > 127) pi = 127;
    float pr = pf - pi;
    v->panl = PAN_C[pi] + pr * (PAN_C[pi + 1] - PAN_C[pi]);
    v->panr = PAN_S[pi] + pr * (PAN_S[pi + 1] - PAN_S[pi]);
    v->vol = p[P_VOICE_VOL] * (1.0f / 127);
}

/* ---------------- audio ---------------- */
static void voice_audio(p8_t *s, voice_t *v, float *out, int n) {
    int OS = s->os;
    for (int i = 0; i < n; i++) {
        float tt = (i + 1) / (float)n, ys[2] = {0, 0};
        for (int k = 0; k < OS; k++) {
            float inc1 = v->inc[0] / OS, inc2 = v->inc[1] / OS;
            float o2 = v->shape[1] < 0 ? 0 : ma_osc(v->shape[1], v->ph[1], inc2, v->duty[1]);
            v->ph[1] += inc2;
            int wrap2 = v->ph[1] >= 1;
            if (wrap2) v->ph[1] -= 1;
            float o1 = v->shape[0] < 0 ? 0 : ma_osc(v->shape[0], v->ph[0], inc1, v->duty[0]) + v->sync_corr;
            v->sync_corr = 0;
            v->ph[0] += inc1;
            if (v->ph[0] >= 1) v->ph[0] -= 1;
            if (LP(s, v->layer, P_SYNC) && wrap2 && v->shape[0] >= 0) {
                float d = v->ph[1] / inc2, now, next;
                ma_sync(v->shape[0], v->duty[0], v->ph[0], inc1, d, &now, &next);
                o1 += now;
                v->sync_corr = next;
                v->ph[0] = v->ph[1] * v->inc[0] / v->inc[1];
            }
            float in = (o1 * (1 - v->mix) + o2 * v->mix + rnd(&v->rng) * v->noise) * 0.5f;
            float g = v->vca_prev + (v->vca - v->vca_prev) * tt;
            float semis = v->cut_prev + (v->cut - v->cut_prev) * tt + v->am * o1;
            float y = ma_ota_lpf(v->lad, v->ladd, lpf_G(OS == 2, semis), v->res, v->four, in);
            ys[k] = ma_tanh(y * g * 0.8f) * 1.25f;
        }
        float a = OS == 1 ? ys[0] : ma_hb_dec(&v->dec, HB_B, MA_HB_B_M, ys[0], ys[1]);
        a *= v->vol;
        out[2 * i] += a * v->panl;
        out[2 * i + 1] += a * v->panr;
    }
}

/* ---------------- engine API ---------------- */
static void browse_follow(p8_t *s) { s->browse_bank = s->cur_bank; s->browse_page = s->cur_prog / PROG_SLOTS; }
static void select_program(p8_t *s, int k) {
    k = clampi(k, 0, 127);
    s->cur_prog = k;
    browse_follow(s);
    memcpy(s->patch, s->banks[s->cur_bank].prog[k], NPATCH);
    s->display_rev++;
}
static void load_bank(p8_t *s, int b) {
    s->cur_bank = clampi(b, 0, s->nbanks - 1);
    browse_follow(s);
    s->display_rev++;
}

static void build_keyhash(void);
static void *p8_create(const char *dir) {
    init_tables();
    build_keyhash();
    p8_t *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    s->cc_vol = 1;
    s->clock_src = 1;
    s->os = P8_DEFAULT_OS;
    s->rng = 0x13579BDFu;
    for (int i = 0; i < MAXV; i++) {
        s->v[i].rng = 0x2468ACE1u + 7919u * (uint32_t)i;
        s->v[i].note = 60;
        s->v[i].cur[0] = s->v[i].cur[1] = 60;
    }
    for (int l = 0; l < 2; l++) { s->ly[l].uni_note = -1; s->ly[l].arp_note = -1; s->ly[l].sp = -1; }
    new_bank(s, "Basic");
    if (dir && *dir) {
        snprintf(s->dir, sizeof s->dir, "%s", dir);
        char sub[PATHLEN];
        snprintf(sub, sizeof sub, "%s/" BANKDIR, dir);
        mkdir(sub, 0755);
        scan_dir(s, sub);
        snprintf(sub, sizeof sub, "%s/" BANKDIR_ALT, dir);
        scan_dir(s, sub);
        scan_dir(s, dir);
    }
    snprintf(s->status, sizeof s->status, "%d banks", s->nbanks);
    load_bank(s, s->nbanks > 1 ? 1 : 0);
    select_program(s, 0);
    return s;
}
static void p8_destroy(void *h) {
    p8_t *s = h;
    if (!s) return;
    for (int i = 0; i < s->nbanks; i++) free(s->banks[i].prog);
    free(s);
}

static void set_patch_value(p8_t *s, int idx, int val) {
    if (idx < 0 || idx >= NPATCH || !PTAB[idx].key[0]) return;
    s->patch[idx] = (uint8_t)clampi(val, PTAB[idx].min, PTAB[idx].max);
}

/* Received controllers that edit layer A directly: the manual lists NRPNs only; these CCs are the common ones. */
static void p8_midi(void *h, const uint8_t *m, int len) {
    p8_t *s = h;
    if (len < 1) return;
    int st = m[0] & 0xF0;
    if (m[0] == 0xF0) {
        if (len >= 6 && m[1] == 0x01 && m[2] == 0x23 && (m[3] == SYX_EDIT) && len >= 4 + PACKED) {
            uint8_t prog[NPROGBYTES + 8];
            syx_unpack(m + 4, PACKED, prog, sizeof prog);
            memcpy(s->patch, prog, NPROGBYTES);
            patch_clamp(s->patch);
            s->display_rev++;
        }
        return;
    }
    if (len < 2) return;
    int d1 = m[1] & 127, d2 = len > 2 ? m[2] & 127 : 0;
    switch (st) {
    case 0x90: if (d2) { note_on(s, d1, d2); break; } /* fall through */
    case 0x80: note_off(s, d1); break;
    case 0xA0: s->t_press = d2 / 127.0f; break;
    case 0xD0: s->t_press = d1 / 127.0f; break;
    case 0xE0: s->bend = ((d1 | (d2 << 7)) - 8192) / 8192.0f; break;
    case 0xC0: select_program(s, d1); break;
    case 0xB0:
        switch (d1) {
        case 1: s->t_wheel = d2 / 127.0f; break;
        case 2: s->t_breath = d2 / 127.0f; break;
        case 4: s->t_foot = d2 / 127.0f; break;
        case 7: s->cc_vol = d2 / 127.0f; break;
        case 11: s->t_expr = d2 / 127.0f; break;
        case 32: if (d2 < s->nbanks) { load_bank(s, d2); s->display_rev++; } break;
        case 64:
            s->pedal = d2 >= 64;
            if (!s->pedal) for (int n = 0; n < 128; n++) if (s->deferred[n]) { s->deferred[n] = 0; note_off(s, n); }
            break;
        case 120: case 123: case 125: all_off(s); if (d1 == 123) { s->t_wheel = s->t_breath = s->t_foot = s->t_press = 0; s->bend = 0; s->cc_vol = 1; } break;
        }
        break;
    }
}

#if defined(__arm__) && !defined(__aarch64__)
static unsigned ftz_on(void) { unsigned f; __asm__ volatile("vmrs %0, fpscr" : "=r"(f)); __asm__ volatile("vmsr fpscr, %0" : : "r"(f | (1u << 24))); return f; }
static void ftz_off(unsigned f) { __asm__ volatile("vmsr fpscr, %0" : : "r"(f)); }
#elif defined(__SSE__)
#include <xmmintrin.h>
static unsigned ftz_on(void) { unsigned f = _mm_getcsr(); _mm_setcsr(f | 0x8040); return f; }
static void ftz_off(unsigned f) { _mm_setcsr(f); }
#else
static unsigned ftz_on(void) { return 0; }
static void ftz_off(unsigned f) { (void)f; }
#endif

static void p8_render(void *h, int16_t *out, int frames) {
    p8_t *s = h;
    unsigned fpcr = ftz_on();
    float buf[2 * CTL];
    for (int f = 0; f < frames; f += CTL) {
        int n = frames - f < CTL ? frames - f : CTL;
        const float k = 0.05f;
        s->wheel += (s->t_wheel - s->wheel) * k; s->press += (s->t_press - s->press) * k;
        s->breath += (s->t_breath - s->breath) * k; s->foot += (s->t_foot - s->foot) * k; s->expr += (s->t_expr - s->expr) * k;
        for (int l = 0; l < 2; l++) layer_clock(s, l);
        memset(buf, 0, sizeof buf);
        for (int i = 0; i < MAXV; i++) {
            voice_t *v = &s->v[i];
            if (!v->on) continue;
            voice_control(s, v, i);
            if (!v->on) continue;
            voice_audio(s, v, buf, n);
        }
        float g = P8_MASTER * s->cc_vol;   /* the soft limiter below keeps chords from clipping hard */
        for (int i = 0; i < 2 * n; i++) {
            float x = ma_tanh(buf[i] * g);
            out[2 * f + i] = (int16_t)lrintf(x * 32767);
        }
    }
    ftz_off(fpcr);
}

/* ---------------- parameters ---------------- */
static short KEYHASH[1024];     /* open addressing: index + 1 of PTAB, 0 = empty */
static unsigned hash_key(const char *k) { unsigned h = 2166136261u; while (*k) h = (h ^ (uint8_t)*k++) * 16777619u; return h; }
static void build_keyhash(void) {
    static int built;
    if (built) return;
    built = 1;
    for (int i = 0; i < NPATCH; i++) {
        if (!PTAB[i].key[0]) continue;
        unsigned h = hash_key(PTAB[i].key) & 1023;
        while (KEYHASH[h]) h = (h + 1) & 1023;
        KEYHASH[h] = (short)(i + 1);
    }
}
static int find_key(const char *k) {
    for (unsigned h = hash_key(k) & 1023; KEYHASH[h]; h = (h + 1) & 1023)
        if (!strcmp(PTAB[KEYHASH[h] - 1].key, k)) return KEYHASH[h] - 1;
    return -1;
}
/* The plugin's controls address the layer being edited (the Edit Layer switch): layer A's keys act on layer B while it is selected.
 * The b_ keys always mean layer B (SysEx, state). */
static int find_key_edit(const p8_t *s, const char *k) {
    int i = find_key(k);
    if (i >= 0 && s->layer_sel && (i < NBASE || (i >= SEQ_A && i < SEQ_A + 64))) i += B_OFF;
    return i;
}
static void note_name(int v, char *b, int n) {
    static const char *nm[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    snprintf(b, (size_t)n, "%s%d", nm[v % 12], v / 12 - 2);
}
static int format_value(const p8_t *s, int i, char *b, int n) {
    int v = s->patch[i];
    const char *f = PTAB[i].fmt;
    if (POPT[i]) snprintf(b, (size_t)n, "%s", POPT[i][clampi(v, 0, PTAB[i].max)]);
    else if (!strcmp(f, "note")) note_name(v, b, n);
    else if (!strcmp(f, "cents")) snprintf(b, (size_t)n, "%+d", v - 50);
    else if (!strcmp(f, "shape")) { if (v == 0) snprintf(b, (size_t)n, "Off"); else if (v == 1) snprintf(b, (size_t)n, "Sawtooth");
        else if (v == 2) snprintf(b, (size_t)n, "Triangle"); else if (v == 3) snprintf(b, (size_t)n, "Saw-Tri"); else snprintf(b, (size_t)n, "Pulse %d", v - 4); }
    else if (!strcmp(f, "bi")) snprintf(b, (size_t)n, "%+d", v - 127);
    else if (!strcmp(f, "lfof")) {
        if (v > 150) snprintf(b, (size_t)n, "%s", SYNC_NAMES[v - 151]);
        else { float hz = p8_lfo_hz(v); snprintf(b, (size_t)n, hz < 10 ? "%.2f Hz" : "%.1f Hz", hz); }
    } else if (!strcmp(f, "tempo")) snprintf(b, (size_t)n, "%d BPM", v);
    else if (!strcmp(f, "onoff")) snprintf(b, (size_t)n, v ? "On" : "Off");
    else if (!strncmp(f, "step", 4)) {
        if (v == 126) snprintf(b, (size_t)n, "Reset");
        else if (v == 127 && f[4] == '1') snprintf(b, (size_t)n, "Rest");
        else snprintf(b, (size_t)n, "%d", v);
    } else snprintf(b, (size_t)n, "%d", v);
    return (int)strlen(b) + 1;
}

static void p8_set_param(void *h, const char *k, const char *val) {
    p8_t *s = h;
    if (!strcmp(k, "state")) {
        /* "P8A <bank> <prog> <layer> <768 hex digits>" */
        int b = 0, p = 0, ly = 0, pos = 0;
        if (sscanf(val, "P8A %d %d %d %n", &b, &p, &ly, &pos) < 3 || pos <= 0) return;
        s->layer_sel = clampi(ly, 0, 1);
        const char *hx = val + pos;
        uint8_t tmp[NPATCH];
        for (int i = 0; i < NPATCH; i++) {
            unsigned x;
            if (sscanf(hx + 2 * i, "%2x", &x) != 1) return;
            tmp[i] = (uint8_t)x;
        }
        memcpy(s->patch, tmp, NPATCH);
        patch_clamp(s->patch);
        if (b >= 0 && b < s->nbanks) s->cur_bank = b;
        s->cur_prog = clampi(p, 0, 127);
        s->display_rev++;
        return;
    }
    int i = find_key_edit(s, k);
    if (i >= 0) { set_patch_value(s, i, atoi(val)); return; }
    int x = atoi(val);
    if (!strcmp(k, "bank")) { if (x != s->cur_bank && x < s->nbanks) { load_bank(s, x); select_program(s, 0); } }
    else if (!strcmp(k, "program")) { if (x != s->cur_prog) select_program(s, x); }
    else if (!strcmp(k, "browse_bank_index")) { if (x >= 0 && x < s->nbanks && x != s->browse_bank) { s->browse_bank = x; s->browse_page = 0; s->display_rev++; } }
    else if (!strcmp(k, "next_browse_bank") || !strcmp(k, "prev_browse_bank")) {
        if (x) { s->browse_bank = (s->browse_bank + (k[0] == 'n' ? 1 : s->nbanks - 1)) % s->nbanks; s->browse_page = 0; s->display_rev++; }
    } else if (!strncmp(k, "bank_slot_", 10)) {
        int b = (s->browse_bank / BANK_SLOTS) * BANK_SLOTS + atoi(k + 10) - 1;
        if (b >= 0 && b < s->nbanks) { s->browse_bank = b; s->browse_page = 0; s->display_rev++; }
    } else if (!strncmp(k, "patch_slot_", 11)) {
        int p = s->browse_page * PROG_SLOTS + atoi(k + 11) - 1;
        if (p >= 0 && p < 128) { s->cur_bank = s->browse_bank; select_program(s, p); }
    } else if (!strcmp(k, "patch_page_index")) { if (x >= 0 && x < PROG_PAGES) { s->browse_page = x; s->display_rev++; } }
    else if (!strcmp(k, "patch_page_next") || !strcmp(k, "patch_page_prev")) {
        if (x) { s->browse_page = (s->browse_page + (k[11] == 'n' ? 1 : PROG_PAGES - 1)) % PROG_PAGES; s->display_rev++; }
    }
    else if (!strcmp(k, "layer")) { s->layer_sel = clampi(x, 0, 1); s->display_rev++; }
    else if (!strcmp(k, "seq_run")) s->seq_run = clampi(x, 0, 2);
    else if (!strcmp(k, "clock_src")) s->clock_src = clampi(x, 0, 1);
    else if (!strcmp(k, "quality")) s->os = clampi(x, 0, 1) == 0 ? 1 : 2;
    else if (!strcmp(k, "lfo_bpm")) s->host_bpm = (float)atof(val);
    else if (!strcmp(k, "transport")) s->transport = x;
}

static int p8_get_param(void *h, const char *k, char *b, int n) {
    p8_t *s = h;
    if (!strcmp(k, "state")) {
        int o = snprintf(b, (size_t)n, "P8A %d %d %d ", s->cur_bank, s->cur_prog, s->layer_sel);
        for (int i = 0; i < NPATCH && o + 3 < n; i++) o += snprintf(b + o, (size_t)(n - o), "%02x", s->patch[i]);
        return o + 1;
    }
    if (!strcmp(k, "display_rev")) return snprintf(b, (size_t)n, "%u", s->display_rev) + 1;
    size_t kl = strlen(k);
    if (kl > 8 && !strcmp(k + kl - 8, "_display")) {
        char base[64];
        snprintf(base, sizeof base, "%.*s", (int)(kl - 8), k);
        int i = find_key_edit(s, base);
        if (i >= 0) return format_value(s, i, b, n);
        if (!strcmp(base, "browse_bank_index")) return snprintf(b, (size_t)n, "%d", s->browse_bank + 1) + 1;
        if (!strcmp(base, "patch_page_index")) return snprintf(b, (size_t)n, "%d", s->browse_page + 1) + 1;
        if (!strcmp(base, "bank")) return snprintf(b, (size_t)n, "%d %s", s->cur_bank + 1, s->banks[s->cur_bank].name) + 1;
        if (!strcmp(base, "program")) return snprintf(b, (size_t)n, "%03d", s->cur_prog + 1) + 1;
        return 0;
    }
    size_t kl2 = strlen(k);
    if (kl2 > 3 && !strcmp(k + kl2 - 3, "_on")) {
        if (!strncmp(k, "bank_slot_", 10)) return snprintf(b, (size_t)n, "%d", (s->browse_bank / BANK_SLOTS) * BANK_SLOTS + atoi(k + 10) - 1 == s->browse_bank) + 1;
        if (!strncmp(k, "patch_slot_", 11))
            return snprintf(b, (size_t)n, "%d", s->browse_bank == s->cur_bank && s->browse_page * PROG_SLOTS + atoi(k + 11) - 1 == s->cur_prog) + 1;
    }
    if (!strncmp(k, "bank_slot_", 10)) {
        int bk = (s->browse_bank / BANK_SLOTS) * BANK_SLOTS + atoi(k + 10) - 1;
        return bk >= 0 && bk < s->nbanks ? snprintf(b, (size_t)n, "%s", s->banks[bk].name) + 1 : snprintf(b, (size_t)n, "%s", "") + 1;
    }
    if (!strncmp(k, "patch_slot_", 11)) {
        int p = s->browse_page * PROG_SLOTS + atoi(k + 11) - 1;
        if (p < 0 || p >= 128) return snprintf(b, (size_t)n, "%s", "") + 1;
        char nm[17];
        memcpy(nm, s->banks[s->browse_bank].prog[p] + NAME_AT, 16);
        nm[16] = 0;
        for (int j = 15; j >= 0 && nm[j] == ' '; j--) nm[j] = 0;
        return snprintf(b, (size_t)n, "%03d %s", p + 1, nm) + 1;
    }
    if (!strcmp(k, "browse_bank_index")) return snprintf(b, (size_t)n, "%d", s->browse_bank) + 1;
    if (!strcmp(k, "browse_bank_name")) return snprintf(b, (size_t)n, "%d %s", s->browse_bank + 1, s->banks[s->browse_bank].name) + 1;
    if (!strcmp(k, "patch_page_index")) return snprintf(b, (size_t)n, "%d", s->browse_page) + 1;
    if (!strcmp(k, "patch_page_text")) return snprintf(b, (size_t)n, "PAGE %d/%d", s->browse_page + 1, PROG_PAGES) + 1;
    if (!strcmp(k, "next_browse_bank") || !strcmp(k, "prev_browse_bank") || !strcmp(k, "patch_page_next") || !strcmp(k, "patch_page_prev")) return snprintf(b, (size_t)n, "0") + 1;
    int i = find_key_edit(s, k);
    if (i >= 0) return snprintf(b, (size_t)n, "%d", s->patch[i]) + 1;
    if (!strcmp(k, "bank")) return snprintf(b, (size_t)n, "%d", s->cur_bank) + 1;
    if (!strcmp(k, "program")) return snprintf(b, (size_t)n, "%d", s->cur_prog) + 1;
    if (!strcmp(k, "layer")) return snprintf(b, (size_t)n, "%d", s->layer_sel) + 1;
    if (!strcmp(k, "patch_name")) {
        char nm[17];
        memcpy(nm, s->patch + NAME_AT, 16);
        nm[16] = 0;
        for (int j = 15; j >= 0 && nm[j] == ' '; j--) nm[j] = 0;
        return snprintf(b, (size_t)n, "%03d %s", s->cur_prog + 1, nm) + 1;
    }
    if (!strcmp(k, "bank_name")) return snprintf(b, (size_t)n, "%s", s->banks[s->cur_bank].name) + 1;
    if (!strcmp(k, "seq_run")) return snprintf(b, (size_t)n, "%d", s->seq_run) + 1;
    if (!strcmp(k, "clock_src")) return snprintf(b, (size_t)n, "%d", s->clock_src) + 1;
    if (!strcmp(k, "quality")) return snprintf(b, (size_t)n, "%d", s->os == 2) + 1;
    if (!strcmp(k, "status")) return snprintf(b, (size_t)n, "%s", s->status) + 1;
    return 0;
}

static const mpc_engine_t ENGINE = {p8_create, p8_destroy, p8_midi, p8_set_param, p8_get_param, p8_render, NULL};
const mpc_engine_t *mpc_engine(void) { return &ENGINE; }
