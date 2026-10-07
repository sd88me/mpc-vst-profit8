/* Prophet '08 SysEx (manual p. 52-54): F0 01 23 <cmd> ... F7, program data in the "packed MS bit" format (7 data bytes per 8
 * MIDI bytes, the first byte of each group holding their top bits, bit 0 = first byte): 384 program bytes in 439 MIDI bytes. */
#pragma once
#include <stdint.h>
#include <stddef.h>
enum { SYX_PROGRAM = 0x02, SYX_EDIT = 0x03, NPROGBYTES = 384, PACKED = 439 };
int syx_unpack(const uint8_t *in, int n, uint8_t *out, int max);      /* -> bytes written */
int syx_pack(const uint8_t *in, int n, uint8_t *out);                 /* -> MIDI bytes written */
/* Walks every message in buf; calls fn for each program or edit-buffer dump (bank 0-1, or -1 for the edit buffer; program number; the 384 bytes). */
void syx_each_program(const uint8_t *buf, size_t len, void (*fn)(void *ctx, int bank, int num, const uint8_t *prog), void *ctx);
int syx_write_program(const uint8_t prog[384], int bank, int num, uint8_t *out);   /* bank < 0: edit buffer; -> message length */
