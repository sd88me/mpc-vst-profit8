#include <string.h>
#include "syx.h"

int syx_unpack(const uint8_t *in, int n, uint8_t *out, int max) {
    int o = 0;
    for (int i = 0; i < n; i += 8) {
        uint8_t m = in[i];
        for (int j = 1; j < 8 && i + j < n && o < max; j++) out[o++] = (uint8_t)((in[i + j] & 0x7F) | (((m >> (j - 1)) & 1) << 7));
    }
    return o;
}

int syx_pack(const uint8_t *in, int n, uint8_t *out) {
    int o = 0;
    for (int i = 0; i < n; i += 7) {
        int hdr = o++;
        uint8_t m = 0;
        for (int j = 0; j < 7 && i + j < n; j++) {
            m |= (uint8_t)(((in[i + j] >> 7) & 1) << j);
            out[o++] = in[i + j] & 0x7F;
        }
        out[hdr] = m;
    }
    return o;
}

void syx_each_program(const uint8_t *buf, size_t len, void (*fn)(void *, int, int, const uint8_t *), void *ctx) {
    size_t i = 0;
    uint8_t prog[NPROGBYTES + 8];
    while (i < len) {
        if (buf[i] != 0xF0) { i++; continue; }
        size_t e = i + 1;
        while (e < len && buf[e] != 0xF7 && !(buf[e] & 0x80)) e++;
        if (e < len && buf[e] == 0xF7 && e - i >= 5 && buf[i + 1] == 0x01 && buf[i + 2] == 0x23) {
            int cmd = buf[i + 3];
            if (cmd == SYX_PROGRAM && e - i == 6 + PACKED) {
                syx_unpack(buf + i + 6, PACKED, prog, sizeof prog);
                fn(ctx, buf[i + 4] & 1, buf[i + 5] & 127, prog);
            } else if (cmd == SYX_EDIT && e - i == 4 + PACKED) {
                syx_unpack(buf + i + 4, PACKED, prog, sizeof prog);
                fn(ctx, -1, 0, prog);
            }
        }
        i = e;
    }
}

int syx_write_program(const uint8_t prog[384], int bank, int num, uint8_t *out) {
    int o = 0;
    out[o++] = 0xF0; out[o++] = 0x01; out[o++] = 0x23;
    if (bank >= 0) { out[o++] = SYX_PROGRAM; out[o++] = (uint8_t)(bank & 1); out[o++] = (uint8_t)(num & 0x7F); }
    else out[o++] = SYX_EDIT;
    o += syx_pack(prog, NPROGBYTES, out + o);
    out[o++] = 0xF7;
    return o;
}
