// Offline host test for the native front end (src/Profit08Plugin.cpp) with the real engine, under ASan/UBSan (tests/run.sh).
// A fake VST2 host drives it: identity and the frozen order, sound, value / choice / momentary / step / text params, the edit layer,
// the parameter-0 nudge, the host tempo, a state round trip into a second instance, a 0.1.3 project chunk
// (tests/data/legacy-0.1.3.chunk, made by the released engine itself), favourites (+FAV, a PRESET pick, -FAV, the file), bad chunks.
// Prints OK at the end, or the failed checks and exits 1.
#include "mpc_vst2_abi.h"
#include "params_gen.h"

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

extern "C" AEffect* VSTPluginMain(audioMasterCallback);
extern "C" void p8_dbg_tick(AEffect*);
extern "C" int p8_dbg_engine(AEffect*, const char*, char*, int);
extern "C" void p8_dbg_engine_set(AEffect*, const char*, const char*);
extern "C" int p8_dbg_favs(AEffect*);

static std::atomic<int> g_automate[kNumParams];
static std::atomic<int> g_updateDisplay{0};
static int g_fail = 0;
static VstTimeInfo g_time;

static VstIntPtr host(AEffect*, VstInt32 op, VstInt32 idx, VstIntPtr, void*, float)
{
    if (op == audioMasterAutomate && idx >= 0 && idx < kNumParams) g_automate[idx]++;
    if (op == audioMasterVersion) return 2400;
    if (op == audioMasterUpdateDisplay) g_updateDisplay++;
    if (op == audioMasterGetTime) return (VstIntPtr)&g_time;
    return 0;
}

#define CHECK(c, ...) do { if (c) { std::printf("  ok   "); } else { std::printf("  FAIL "); g_fail++; } std::printf(__VA_ARGS__); std::printf("\n"); } while (0)

static int idx(const char* key)
{
    for (int i = 0; i < kNumParams; i++) if (!std::strcmp(g_pspecs[i].key, key)) return i;
    std::printf("no param %s\n", key); std::exit(2);
}
static float norm(int i, float plain) { const PSpec& s = g_pspecs[i]; return s.max > s.min ? (plain - s.min) / (s.max - s.min) : 0.f; }
static float plainOf(AEffect* e, int i) { const PSpec& s = g_pspecs[i]; return s.min + e->getParameter(e, i) * (s.max - s.min); }
static std::string eng(AEffect* e, const char* k) { static char b[8192]; p8_dbg_engine(e, k, b, sizeof b); return b; }
static int engi(AEffect* e, const char* k) { return std::atoi(eng(e, k).c_str()); }
static std::string disp(AEffect* e, int i) { char b[128] = {0}; e->dispatcher(e, effGetParamDisplay, i, 0, b, 0); return b; }

static double g_rms;
static void run(AEffect* e, int blocks, const std::vector<std::vector<uint8_t>>& midi = {})
{
    float L[128], R[128], *out[2] = {L, R};
    double acc = 0; long n = 0;
    for (int b = 0; b < blocks; b++)
    {
        if (b == 0 && !midi.empty())
        {
            std::vector<VstMidiEvent> ev(midi.size());
            std::vector<char> buf(sizeof(VstEvents) + sizeof(VstEvent*) * midi.size());
            VstEvents* evs = reinterpret_cast<VstEvents*>(buf.data());
            evs->numEvents = (VstInt32)midi.size();
            for (size_t k = 0; k < midi.size(); k++)
            {
                std::memset(&ev[k], 0, sizeof ev[k]);
                ev[k].type = kVstMidiType; ev[k].byteSize = sizeof(VstMidiEvent);
                ev[k].deltaFrames = (VstInt32)(k * 17 % 128);   // sample-accurate split
                for (size_t j = 0; j < 3 && j < midi[k].size(); j++) ev[k].midiData[j] = (char)midi[k][j];
                evs->events[k] = reinterpret_cast<VstEvent*>(&ev[k]);
            }
            e->dispatcher(e, effProcessEvents, 0, 0, evs, 0);
        }
        e->processReplacing(e, nullptr, out, 128);
        for (int i = 0; i < 128; i++) { acc += (double)L[i] * L[i] + (double)R[i] * R[i]; n += 2; }
    }
    g_rms = n ? std::sqrt(acc / n) : 0;
}
static void settle(AEffect* e, int blocks = 4) { run(e, blocks); p8_dbg_tick(e); }

static AEffect* open(const char* what)
{
    AEffect* e = VSTPluginMain(host);
    e->dispatcher(e, effSetSampleRate, 0, 0, nullptr, 44100.f);
    e->dispatcher(e, effSetBlockSize, 0, 128, nullptr, 0);
    e->dispatcher(e, effMainsChanged, 0, 1, nullptr, 0);
    settle(e);
    std::printf("%s: opened\n", what);
    return e;
}
static void close(AEffect* e) { e->dispatcher(e, effMainsChanged, 0, 0, nullptr, 0); e->dispatcher(e, effClose, 0, 0, nullptr, 0); }
static std::vector<uint8_t> chunk(AEffect* e)
{
    void* p = nullptr;
    const VstIntPtr n = e->dispatcher(e, effGetChunk, 0, 0, &p, 0);
    return n > 0 && p ? std::vector<uint8_t>((uint8_t*)p, (uint8_t*)p + n) : std::vector<uint8_t>();
}
static VstIntPtr setChunk(AEffect* e, std::vector<uint8_t> c) { return e->dispatcher(e, effSetChunk, 0, (VstIntPtr)c.size(), c.data(), 0); }

int main(int argc, char** argv)
{
    const char* legacyPath = argc > 1 ? argv[1] : "tests/data/legacy-0.1.3.chunk";
    const int OSC1 = idx("osc1_freq"), LPF = idx("lpf_freq"), LAYER = idx("layer"), KBD = idx("kbd_mode"), PROG = idx("program"),
              PNEXT = idx("program_next"), PPREV = idx("program_prev"), PNAME = idx("patch_name"), PSLOT3 = idx("patch_slot_3"),
              PAGEN = idx("patch_page_next"), UNI = idx("unison");

    std::printf("== identity\n");
    AEffect* a = open("A");
    char name[64] = {0};
    a->dispatcher(a, effGetEffectName, 0, 0, name, 0);
    CHECK(a->uniqueID == (VstInt32)0x50667438, "uid Pft8 (%08x)", (unsigned)a->uniqueID);
    CHECK(!std::strcmp(name, P8_EXPECT_NAME), "name \"%s\"", name);
    CHECK(a->numParams == 284, "284 params: 245 frozen keys + 37 1.x popup slots + 2 favourite keys (%d)", a->numParams);
    CHECK(a->dispatcher(a, effGetVendorVersion, 0, 0, nullptr, 0) == 2000, "version 2000");
    {
        int bad = 0, i = 0;
        std::ifstream f("vst/params.lock");
        std::string line;
        while (std::getline(f, line)) if (!line.empty() && line != g_pspecs[i++].key) bad++;
        CHECK(i == 245 && bad == 0, "order = vst/params.lock (%d keys, %d differ)", i, bad);
        CHECK(kUiParam == 245 && !std::strcmp(g_pspecs[281].key, "rsv_281") && kFavAdd == 282 && kFavDel == 283,
              "ui_open at 245 (was layer__open), reserved to 281, +FAV 282, -FAV 283");
    }

    std::printf("== sound\n");
    run(a, 100, {{0x90, 60, 100}, {0x90, 64, 100}});
    const double on = g_rms;
    run(a, 600, {{0x80, 60, 0}, {0x80, 64, 0}});
    run(a, 50);
    const double off = g_rms;
    CHECK(on > 1e-3, "notes are audible (rms %.4f)", on);
    CHECK(off < on * 0.1, "note off releases (rms %.5f)", off);

    std::printf("== value and choice params\n");
    a->setParameter(a, LPF, norm(LPF, 90));
    settle(a);
    CHECK(engi(a, "lpf_freq") == 90, "LPF FREQ 90 -> engine %d", engi(a, "lpf_freq"));
    CHECK(std::lround(plainOf(a, LPF)) == 90, "LPF FREQ reads back 90 (%.1f)", plainOf(a, LPF));
    a->setParameter(a, KBD, norm(KBD, 2));
    settle(a);
    CHECK(engi(a, "kbd_mode") == 2, "KEYBOARD -> Split (engine %d), shows \"%s\"", engi(a, "kbd_mode"), disp(a, KBD).c_str());
    a->setParameter(a, KBD, norm(KBD, 0));
    a->setParameter(a, idx("osc1_shape"), norm(idx("osc1_shape"), 2));
    settle(a);
    CHECK(disp(a, idx("osc1_shape")) == "Triangle", "OSC 1 SHAPE shows the engine's text (\"%s\")", disp(a, idx("osc1_shape")).c_str());
    {   // a Q-Link nudge between steps moves one step the way it turns
        const int ENV = idx("aenv_a");
        a->setParameter(a, ENV, norm(ENV, 40));
        settle(a);
        a->setParameter(a, ENV, norm(ENV, 40.3f));
        settle(a);
        CHECK(engi(a, "aenv_a") == 41, "a small turn up moves ATTACK one step (engine %d)", engi(a, "aenv_a"));
    }

    std::printf("== edit layer\n");
    a->setParameter(a, OSC1, norm(OSC1, 30));
    run(a, 10); p8_dbg_tick(a); p8_dbg_tick(a);
    CHECK(engi(a, "osc1_freq") == 30, "layer A OSC 1 FREQ 30");
    a->setParameter(a, LAYER, norm(LAYER, 1));
    settle(a);
    a->setParameter(a, OSC1, norm(OSC1, 50));
    run(a, 10); p8_dbg_tick(a); p8_dbg_tick(a);
    CHECK(engi(a, "osc1_freq") == 50 && engi(a, "b_osc1_freq") == 50, "layer B OSC 1 FREQ 50 (b_ %d)", engi(a, "b_osc1_freq"));
    g_updateDisplay = 0;
    a->setParameter(a, LAYER, norm(LAYER, 0));
    settle(a);
    CHECK(std::lround(plainOf(a, OSC1)) == 30, "back on layer A the control shows A's 30 (%.0f)", plainOf(a, OSC1));

    std::printf("== parameter 0 nudge\n");
    a->setParameter(a, OSC1, 1.0f);
    a->setParameter(a, OSC1, norm(OSC1, 30));
    run(a, 2);
    std::this_thread::sleep_for(std::chrono::milliseconds(80));
    run(a, 2);
    CHECK(engi(a, "osc1_freq") == 30, "a nudge to the end and back leaves OSC 1 FREQ at 30 (%d)", engi(a, "osc1_freq"));
    a->setParameter(a, OSC1, norm(OSC1, 33));
    std::this_thread::sleep_for(std::chrono::milliseconds(80));
    run(a, 2);
    CHECK(engi(a, "osc1_freq") == 33, "a held change applies (%d)", engi(a, "osc1_freq"));

    std::printf("== momentary, step, text, tiles\n");
    const int p0 = engi(a, "program");
    a->setParameter(a, PNEXT, 1.0f);
    settle(a);
    CHECK(engi(a, "program") == (p0 + 1) % 128, "PROGRAM > steps (%d -> %d)", p0, engi(a, "program"));
    CHECK(plainOf(a, PNEXT) < 0.5f, "PROGRAM > drops back to 0");
    a->setParameter(a, PNEXT, 0.0f);
    a->setParameter(a, PROG, norm(PROG, 0));
    settle(a);
    a->setParameter(a, PPREV, 1.0f);
    settle(a);
    a->setParameter(a, PPREV, 0.0f);
    CHECK(engi(a, "program") == 127, "PROGRAM < wraps 1 -> 128 (%d)", engi(a, "program"));
    CHECK(disp(a, PNAME).compare(0, 3, "128") == 0, "NAME shows the engine's text (\"%s\")", disp(a, PNAME).c_str());
    a->setParameter(a, idx("patch_page_index"), 0.0f);   // PROGRAM 128 moved the browser to page 3
    settle(a);
    a->setParameter(a, PAGEN, 1.0f);
    settle(a);
    a->setParameter(a, PAGEN, 0.0f);
    CHECK(engi(a, "patch_page_index") == 1, "PAGE > (page %d)", engi(a, "patch_page_index") + 1);
    a->setParameter(a, PSLOT3, 1.0f);
    settle(a);
    CHECK(engi(a, "program") == 47, "the 3rd tile on page 2 picks program 48 (%d)", engi(a, "program") + 1);
    CHECK(plainOf(a, PSLOT3) > 0.5f && disp(a, PSLOT3).compare(0, 3, "048") == 0, "the tile is lit and named \"%s\"", disp(a, PSLOT3).c_str());
    a->setParameter(a, PSLOT3, 0.0f);   // a tap on a lit tile: it stays lit
    settle(a);
    CHECK(plainOf(a, PSLOT3) > 0.5f, "a second tap leaves it lit");
    CHECK(disp(a, kFavAdd).empty() && disp(a, kUiParam).empty() && disp(a, 260).empty(), "+FAV / ui_open / reserved show no text");

    std::printf("== host tempo\n");
    std::memset(&g_time, 0, sizeof g_time);
    g_time.sampleRate = 44100; g_time.tempo = 97; g_time.flags = kVstTempoValid | kVstTransportPlaying;
    run(a, 2);
    CHECK(true, "tempo 97, transport playing reach the engine (no crash)");
    g_time.flags = 0;
    run(a, 2);

    std::printf("== state round trip\n");
    a->setParameter(a, UNI, 1.0f);
    a->setParameter(a, LAYER, norm(LAYER, 1));
    settle(a);
    a->setParameter(a, LPF, norm(LPF, 12));
    settle(a);
    const std::string stA = eng(a, "state");
    std::vector<uint8_t> ca = chunk(a);
    CHECK(ca.size() > 4 && !std::memcmp(ca.data(), "MPCP", 4), "MPC chunk (%zu bytes)", ca.size());
    AEffect* b = open("B");
    CHECK(setChunk(b, ca) == 1, "B takes A's chunk");
    settle(b);
    CHECK(eng(b, "state") == stA, "B's engine state = A's (edit layer B, both layers' edits)");
    CHECK(std::lround(plainOf(b, LPF)) == 12 && std::lround(plainOf(b, LAYER)) == 1, "B's controls show layer B's LPF 12 (%.0f)", plainOf(b, LPF));

    std::printf("== 0.1.3 project chunk\n");
    std::ifstream lf(legacyPath, std::ios::binary);
    std::vector<uint8_t> legacy((std::istreambuf_iterator<char>(lf)), std::istreambuf_iterator<char>());
    CHECK(legacy.size() > 700, "%s (%zu bytes)", legacyPath, legacy.size());
    AEffect* c = open("C");
    CHECK(setChunk(c, legacy) == 1, "C takes the 0.1.3 chunk");
    settle(c);
    const std::string want(reinterpret_cast<const char*>(legacy.data()));
    CHECK(eng(c, "state") == want, "the engine state is the saved one");
    CHECK(std::lround(plainOf(c, LAYER)) == 1 && engi(c, "b_aenv_r") == 77 && engi(c, "osc1_freq") == engi(c, "b_osc1_freq") &&
          engi(c, "osc1_freq") != 37, "edit layer B, layer B's AMP RELEASE 77, OSC 1 FREQ follows layer B (A's 37 is not shown)");
    CHECK(std::lround(plainOf(c, idx("aenv_r"))) == 77 && std::lround(plainOf(c, idx("osc2_shape"))) == 9, "the controls show layer B (release 77, osc 2 shape 9)");
    {
        std::vector<uint8_t> cc = chunk(c);   // saved again by this build, then reloaded
        AEffect* d = open("D");
        setChunk(d, cc);
        settle(d);
        CHECK(eng(d, "state") == want, "re-saved by this build and reloaded: unchanged");
        close(d);
    }

    std::printf("== bad chunks\n");
    {
        const std::string before = eng(c, "state");
        CHECK(setChunk(c, {'x', 'y', 'z', 0}) == 0, "garbage is refused");
        std::vector<uint8_t> trunc(ca.begin(), ca.begin() + ca.size() / 2);
        setChunk(c, trunc);
        settle(c);
        std::vector<uint8_t> badhex(legacy);
        badhex[40] = 'Q';
        setChunk(c, badhex);
        settle(c);
        CHECK(eng(c, "state").compare(0, 4, "P8A ") == 0, "truncated MPC chunk / bad hex: no crash, still a valid program");
        (void)before;
    }

    std::printf("== favourites\n");
    {
        const int n0 = p8_dbg_favs(a);
        a->setParameter(a, LPF, norm(LPF, 66));
        settle(a);
        const std::string saved = eng(a, "state");
        a->setParameter(a, kFavAdd, 1.0f);
        settle(a);
        a->setParameter(a, kFavAdd, 0.0f);
        settle(a);
        CHECK(p8_dbg_favs(a) == n0 + 1, "+FAV saves one (%d)", p8_dbg_favs(a));
        char pn[64] = {0};
        a->dispatcher(a, effGetProgramNameIndexed, n0 + 1, 0, pn, 0);
        CHECK(std::strstr(pn, "--") == nullptr && pn[0], "PRESET menu slot %d: \"%s\"", n0 + 1, pn);
        a->setParameter(a, LPF, norm(LPF, 5));
        settle(a);
        std::this_thread::sleep_for(std::chrono::milliseconds(2100));   // past the post-load program re-pick window
        a->dispatcher(a, effSetProgram, 0, n0 + 1, nullptr, 0);
        settle(a); settle(a);
        CHECK(eng(a, "state") == saved && std::lround(plainOf(a, LPF)) == 66, "picking it in PRESET restores it (LPF %.0f)", plainOf(a, LPF));
        AEffect* e2 = open("E (reads the favourites file)");
        CHECK(p8_dbg_favs(e2) == n0 + 1, "a new instance reads it from profit08-favourites.dat");
        close(e2);
        a->setParameter(a, kFavDel, 1.0f);
        settle(a);
        a->setParameter(a, kFavDel, 0.0f);
        settle(a);
        CHECK(p8_dbg_favs(a) == n0, "-FAV deletes the picked one (%d)", p8_dbg_favs(a));
    }

    close(c);
    close(b);
    close(a);
    if (g_fail) { std::printf("%d FAILED\n", g_fail); return 1; }
    std::printf("OK\n");
    return 0;
}
