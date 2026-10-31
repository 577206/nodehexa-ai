#pragma once
#include "eye_animation.h"
void eyes_start(void);
/* Temporary expression, returns to live conversation state after <= 10 seconds. */
void eyes_expression(eye_mode_t mode, unsigned duration_ms);

/* mode -1 returns immediately to automatic conversation animation. */
void eyes_control(int mode, unsigned duration_ms, unsigned contrast);
unsigned eyes_ready_mask(void);
unsigned eyes_current_mode(void);
unsigned eyes_contrast(void);
