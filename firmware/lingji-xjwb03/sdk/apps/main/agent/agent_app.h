#ifndef AGENT_APP_H
#define AGENT_APP_H

#include <stdint.h>
#include "qm_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* 创建 agent。唤醒词到来且云已连上时才 start。 */
int agent_app_init(void *iot_handle);
/* 请求本地静默：关掉麦上行并标记会话空闲，不退出会话，下次唤醒重开上行。 */
int agent_app_leave(void);
/* 返回 1 表示会话已 start 且尚未结束（本地静默期间仍为 1）。 */
int agent_app_is_active(void);
int agent_app_is_cloud_connected(void);
/* Network may be up before Agent credentials are ready for speak requests. */
int agent_app_is_corpus_ready(void);
int agent_app_is_uplink_enabled(void);
/* 以本地提示音方式播一段已按 qm_audio 线上格式编好的音频；会话未创建时返回 -QM_EINIT。 */
int agent_app_play_local_audio(const void *data, uint32_t len);

/* Stop cloud/local output and pause the physical capture path. */
int agent_app_abort_output(void);

/* Ask the cloud agent to speak one application-provided sentence. */
int agent_app_user_corpus(const char *text);

/* Wait until the local TTS queue and speaker have drained. */
int agent_app_wait_tts_complete(uint32_t timeout_ms);

/* Reserve or release the shared audio path for resource playback. */
int agent_app_set_resource_mode(qm_bool active);

#ifdef __cplusplus
}
#endif

#endif
