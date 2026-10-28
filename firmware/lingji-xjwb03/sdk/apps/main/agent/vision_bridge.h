#pragma once

/* Register the local serial command that forwards a short visual observation
 * to the already configured cloud voice Agent. */
int vision_bridge_init(void);

/* Forward only final, post-wake ASR text to the local host for on-demand
 * visual-intent classification. The host does not receive microphone audio. */
void vision_bridge_on_asr(const char *text, int truncated);
