#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Register the local serial command that forwards a short visual observation
 * to the already configured cloud voice Agent. */
int vision_bridge_init(void);

/* Forward only final, post-wake ASR text to the local host for on-demand
 * visual-intent classification. The host does not receive microphone audio. */
void vision_bridge_on_asr(const char *text, int truncated);

/* Shared by the serial console and authenticated LAN bridge. */
bool vision_bridge_submit(const char *text, size_t length);
bool vision_bridge_cloud_connected(void);
bool vision_bridge_active(void);
bool vision_bridge_uplink_enabled(void);
bool vision_bridge_corpus_ready(void);
uint32_t vision_bridge_last_asr(char *text, size_t capacity);
