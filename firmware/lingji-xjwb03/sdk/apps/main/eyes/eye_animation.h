#pragma once
#include <stdint.h>
#define EYE_WIDTH 128
#define EYE_HEIGHT 64
#define EYE_BYTES 1024
/* One display per eye; SH1106/SSD1306 page-format framebuffer. */
typedef enum { EYE_IDLE, EYE_LISTEN, EYE_THINK, EYE_SPEAK, EYE_HAPPY,
 EYE_SURPRISE, EYE_SLEEP, EYE_WINK, EYE_OPEN, EYE_MODE_COUNT } eye_mode_t;
void eye_render(uint8_t out[EYE_BYTES], unsigned side, eye_mode_t mode,
                uint32_t uptime_ms, uint32_t mode_elapsed_ms);
