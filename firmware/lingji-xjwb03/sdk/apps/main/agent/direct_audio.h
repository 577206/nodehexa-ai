#pragma once
#include <stddef.h>
#include <stdint.h>

/* LXA1 + little-endian generation u32 + state u8 + reserved u8 + count u16;
 * each native Opus packet has a little-endian u16 length. States: 0 idle,
 * 1 listening, 2 waiting, 3 playing. Downlink: generation u32, command u8,
 * then length-prefixed packets. Commands: 1 begin, 2 packets, 3 end,
 * 4 hold microphone, 5 idle, 6 extend current listening window.
 * Only a hardware wake event can start a new generation. */
int direct_audio_init(void);
size_t direct_audio_read(uint8_t *out, size_t capacity);
/* 0 accepted; 1 stale/idle; 2 full; 3 malformed; 4 unavailable. */
int direct_audio_write(const uint8_t *data, size_t length);
unsigned direct_audio_state(void);
uint32_t direct_audio_generation(void);
