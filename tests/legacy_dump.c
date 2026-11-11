/* Builds against the RELEASED 0.1.3 engine (tests/make_legacy_chunk.sh) and prints the chunk that build's wrapper saved: the engine's
 * "state" string (vst2_wrap.c effGetChunk = eng_get("state")). No banks: the engine's init program, edited here, so the chunk holds
 * no factory or third-party patch bytes. */
#include <stdio.h>
#include "engine.h"
int main(int argc, char **argv) {
    const mpc_engine_t *e = mpc_engine();
    void *s = e->create(argc > 1 ? argv[1] : ".");
    e->set_param(s, "osc1_freq", "37");
    e->set_param(s, "lpf_freq", "88");
    e->set_param(s, "unison", "1");
    e->set_param(s, "layer", "1");          /* edits below go to layer B; the saved edit layer is B */
    e->set_param(s, "osc2_shape", "9");
    e->set_param(s, "aenv_r", "77");
    e->set_param(s, "kbd_mode", "1");
    static char buf[8192];
    e->get_param(s, "state", buf, sizeof buf);
    fputs(buf, stdout);
    e->destroy(s);
    return 0;
}
