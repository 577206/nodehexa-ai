#include "agent_app.h"
#include "ljyd_cloud.h"
#include "qm_config.h"

#if defined(CONFIG_LJYD_PLAYBACK_SUPPORT) && CONFIG_LJYD_PLAYBACK_SUPPORT
#include "playback.h"
#endif

#include "cJSON.h"
#include "qm_agent.h"
/* qdev has no public auth getter; keep this compatibility access app-local. */
#include "qm_agent_internal.h"
#include "qm_audio.h"
#include "qm_event.h"
#include "qm_http_client.h"
#include "qm_iot_dynreg.h"
#include "qm_log.h"
#include "qm_string.h"
#include "qm.h"
#include "qm_kernel.h"
#include "qm_work.h"
#include "voice.h"
#if defined(CONFIG_APP_CAMERA_TEST) && CONFIG_APP_CAMERA_TEST
#include "vision_bridge.h"
#endif

#define LOG_TAG "agent"

static qm_agent_handle_t s_agent;
static uint8_t s_cloud_connected;
static uint8_t s_agent_started;
static uint8_t s_event_registered;
static qm_sem_t s_tts_complete_sem;
static uint8_t s_tts_complete_sem_ready;
static volatile uint8_t s_waiting_tts_complete;
static volatile uint8_t s_tts_wait_aborted;
static volatile uint8_t s_tts_text_seen;
static volatile uint8_t s_tts_speaking_seen;
static volatile uint8_t s_tts_playback_started;
static volatile uint8_t s_tts_playback_failed;
static volatile int s_tts_playback_error;
static volatile uint8_t s_tts_silent_seen;
static volatile uint8_t s_tts_input_complete_posted;

static qm_task_t s_worker_task;
static qm_sem_t s_worker_sem;
static uint8_t s_worker_ready;
static qm_work_t s_idle_work;
static volatile uint8_t s_pending_idle;
static volatile int s_dialog_state;
/* Start with cloud microphone upload closed; only a local wake opens it. */
static volatile uint8_t s_session_idle = 1U;
static volatile uint8_t s_resource_active;

/* 投递给 worker 的请求类型。 */
#define AGENT_IDLE_NONE     0U
#define AGENT_IDLE_REQUEST  1U

static void abort_tts_wait(void);
static void agent_sync_upload(void);

/*
 * Agora currently reports the end of a custom-corpus reply as dialog=silent,
 * but does not emit QM_AGENT_EVENT_TTS_INPUT_COMPLETE.  Only close the input
 * after qm_agent has admitted and started local playback; then queue the
 * normalized boundary on qm_agent's control task so the PUSH audio operation
 * can drain.
 */
static void finish_custom_tts_input_if_ready(void)
{
    qm_agent_event_t *event;
    int ret;

    if (!s_waiting_tts_complete || !s_tts_text_seen ||
        !s_tts_speaking_seen || !s_tts_playback_started ||
        !s_tts_silent_seen ||
        s_tts_wait_aborted || s_tts_input_complete_posted || s_agent == NULL) {
        return;
    }

    event = (qm_agent_event_t *)qm_malloc(sizeof(*event));
    if (event == NULL) {
        QM_LOGE(LOG_TAG, "tts input complete alloc failed");
        return;
    }
    qm_memset(event, 0, sizeof(*event));
    event->id = QM_AGENT_EVENT_TTS_INPUT_COMPLETE;
    event->source = QM_AGENT_EVENT_SOURCE_TRANSPORT;

    /* Mark before posting because the control task consumes this asynchronously. */
    s_tts_input_complete_posted = 1U;
    ret = qm_agent_control_post_event(s_agent, event);
    if (ret != QM_EOK) {
        s_tts_input_complete_posted = 0U;
        QM_LOGW(LOG_TAG, "tts input complete post failed ret=%d", ret);
        return;
    }
    QM_LOGI(LOG_TAG, "tts input complete queued after dialog silent");
}

#define AGENT_CORPUS_URL_MAX       160U
#define AGENT_CORPUS_TIMEOUT_MS    15000U
#define AGENT_AUDIO_IDLE_TIMEOUT_MS 3000U
#define AGENT_AUDIO_IDLE_POLL_MS      10U

static int wait_agent_audio_idle(void)
{
    uint32_t waited_ms = 0U;

    while (s_agent != NULL && qm_agent_audio_engine_stream_active(s_agent)) {
        if (waited_ms >= AGENT_AUDIO_IDLE_TIMEOUT_MS) {
            QM_LOGW(LOG_TAG, "agent audio cleanup timeout=%u",
                    (unsigned)AGENT_AUDIO_IDLE_TIMEOUT_MS);
            return -QM_ETIMEOUT;
        }
        qm_msleep(AGENT_AUDIO_IDLE_POLL_MS);
        waited_ms += AGENT_AUDIO_IDLE_POLL_MS;
    }
    return QM_EOK;
}

static const char *life_name(qm_agent_state_t state)
{
    switch (state) {
        case QM_AGENT_STATE_IDLE:
            return "idle";
        case QM_AGENT_STATE_READY:
            return "ready";
        case QM_AGENT_STATE_STARTING:
            return "starting";
        case QM_AGENT_STATE_RUNNING:
            return "running";
        case QM_AGENT_STATE_STOPPING:
            return "stopping";
        case QM_AGENT_STATE_ERROR:
            return "error";
        case QM_AGENT_STATE_NONE:
        default:
            return "none";
    }
}

static inline uint8_t agent_state_is_active(qm_agent_state_t state)
{
    return (state == QM_AGENT_STATE_STARTING ||
            state == QM_AGENT_STATE_RUNNING) ? 1U : 0U;
}

static const char *dialog_name(qm_agent_dialog_state_t state)
{
    switch (state) {
        case QM_AGENT_DIALOG_STATE_SILENT:
            return "silent";
        case QM_AGENT_DIALOG_STATE_LISTENING:
            return "listening";
        case QM_AGENT_DIALOG_STATE_THINKING:
            return "thinking";
        case QM_AGENT_DIALOG_STATE_SPEAKING:
            return "speaking";
        case QM_AGENT_DIALOG_STATE_NONE:
        default:
            return "none";
    }
}

/* 会话内最后一次对话活动后多久进入本地静默。 */
#define AGENT_IDLE_SILENCE_MS  (15U * 1000U)

/* 空闲超时回调跑在默认事件循环上，只投递请求，不做阻塞调用。 */
static void agent_idle_silence_timeout(void *arg)
{
    (void)arg;
    s_pending_idle = AGENT_IDLE_REQUEST;
    (void)qm_sem_signal(&s_worker_sem);
}

static void agent_idle_timer_start(void)
{
    (void)qm_post_delayed_action(&s_idle_work, agent_idle_silence_timeout, NULL,
                                 AGENT_IDLE_SILENCE_MS);
}

static void agent_idle_timer_stop(void)
{
    (void)qm_cancel_delayed_action(&s_idle_work);
}

/* 按对话活动计时，连续无活动满 AGENT_IDLE_SILENCE_MS 才进入本地静默。 */
static void agent_session_touch(void)
{
    if (s_agent_started) {
        agent_idle_timer_start();
    }
}

static void on_agent_event(void *event_handler_arg,
                           qm_event_base_t event_base,
                           int32_t event_id,
                           void *event_data,
                           size_t event_data_size)
{
    const qm_agent_event_notice_t *notice = (const qm_agent_event_notice_t *)event_data;

    (void)event_handler_arg;
    if (event_base != QM_AGENT_EVENT_BASE || notice == NULL ||
        event_data_size != sizeof(*notice)) {
        return;
    }

    switch ((qm_agent_event_id_t)event_id) {
        case QM_AGENT_EVENT_STATE_CHANGED:
            QM_LOGI(LOG_TAG, "state %s -> %s",
                    life_name(notice->data.state.old_state),
                    life_name(notice->data.state.new_state));
            s_agent_started = agent_state_is_active(notice->data.state.new_state);
            agent_sync_upload();
            break;
        case QM_AGENT_EVENT_CONNECTED:
            QM_LOGI(LOG_TAG, "agora connected");
            break;
        case QM_AGENT_EVENT_DISCONNECTED:
            QM_LOGW(LOG_TAG, "agora disconnected");
            s_agent_started = 0;
            s_session_idle = 1U;
            s_dialog_state = QM_AGENT_DIALOG_STATE_NONE;
            agent_idle_timer_stop();
            break;
        case QM_AGENT_EVENT_ASR:
            QM_LOGI(LOG_TAG, "asr final=%d bytes=%u",
                    notice->data.text.final,
                    (unsigned)qm_strlen(notice->data.text.text));
#if defined(CONFIG_APP_CAMERA_TEST) && CONFIG_APP_CAMERA_TEST
            if (notice->data.text.final) {
                vision_bridge_on_asr(notice->data.text.text,
                                     notice->data.text.truncated);
            }
#endif
            break;
        case QM_AGENT_EVENT_TTS:
            QM_LOGI(LOG_TAG, "tts final=%d text=%s",
                    notice->data.text.final,
                    notice->data.text.text);
            if (s_waiting_tts_complete && notice->data.text.text[0] != '\0') {
                s_tts_text_seen = 1U;
                finish_custom_tts_input_if_ready();
            }
            break;
        case QM_AGENT_EVENT_AGENT_TEXT:
            QM_LOGI(LOG_TAG, "agent text final=%d text=%s",
                    notice->data.text.final,
                    notice->data.text.text);
            break;
        case QM_AGENT_EVENT_AGENT_STATE:
            QM_LOGI(LOG_TAG, "dialog=%s",
                    dialog_name(notice->data.agent_state.state));
            s_dialog_state = (int)notice->data.agent_state.state;
            if (s_session_idle) {
                agent_sync_upload();
            }
            /* The core may re-enable upload when it reports speaking. The
             * custom-corpus transaction owns upload until its local TTS ends. */
            if (s_waiting_tts_complete && s_agent != NULL) {
                qm_agent_set_upload_enabled(s_agent, QM_FALSE);
            }
            if (s_waiting_tts_complete) {
                if (notice->data.agent_state.state == QM_AGENT_DIALOG_STATE_SPEAKING) {
                    s_tts_speaking_seen = 1U;
                    s_tts_silent_seen = 0U;
                } else if (notice->data.agent_state.state == QM_AGENT_DIALOG_STATE_SILENT) {
                    s_tts_silent_seen = 1U;
                    finish_custom_tts_input_if_ready();
                }
            }
            break;
        case QM_AGENT_EVENT_TTS_PLAYBACK_STARTED:
            if (s_waiting_tts_complete) {
                s_tts_playback_started = 1U;
                finish_custom_tts_input_if_ready();
            }
            QM_LOGI(LOG_TAG, "tts playback started generation=%u",
                    (unsigned)notice->generation);
            break;
        case QM_AGENT_EVENT_TTS_PLAYBACK_FAILED:
            if (s_waiting_tts_complete) {
                s_tts_playback_failed = 1U;
                s_tts_playback_error = notice->code != QM_EOK ?
                                       notice->code : -QM_EIO;
                if (s_tts_complete_sem_ready) {
                    (void)qm_sem_signal(&s_tts_complete_sem);
                }
            }
            QM_LOGE(LOG_TAG, "tts playback failed generation=%u code=%d",
                    (unsigned)notice->generation, notice->code);
            break;
        case QM_AGENT_EVENT_TTS_PLAYBACK_COMPLETE:
            if (s_waiting_tts_complete && s_tts_complete_sem_ready) {
                (void)qm_sem_signal(&s_tts_complete_sem);
            }
            QM_LOGI(LOG_TAG, "tts playback complete generation=%u",
                    (unsigned)notice->generation);
            break;
        case QM_AGENT_EVENT_ERROR:
            QM_LOGE(LOG_TAG, "agent error code=%d msg=%s",
                    notice->code,
                    notice->data.text.text);
            agent_idle_timer_stop();
            break;
        default:
            QM_LOGD(LOG_TAG, "agent event id=%d", (int)event_id);
            break;
    }

    switch ((qm_agent_event_id_t)event_id) {
        case QM_AGENT_EVENT_ASR:
        case QM_AGENT_EVENT_TTS:
        case QM_AGENT_EVENT_AGENT_TEXT:
        case QM_AGENT_EVENT_AGENT_STATE:
        case QM_AGENT_EVENT_TTS_PLAYBACK_STARTED:
        case QM_AGENT_EVENT_TTS_PLAYBACK_COMPLETE:
        case QM_AGENT_EVENT_TTS_PLAYBACK_FAILED:
            agent_session_touch();
            break;
        default:
            break;
    }
}

static int register_agent_events(void)
{
    int ret;

    if (s_event_registered) {
        return QM_EOK;
    }
    ret = qm_event_default_create();
    if (ret != QM_EOK && ret != -QM_EINIT) {
        return ret;
    }
    ret = qm_event_handler_register(QM_AGENT_EVENT_BASE,
                                    QM_EVENT_ANY_ID,
                                    on_agent_event,
                                    NULL);
    if (ret == QM_EOK) {
        s_event_registered = 1;
    }
    return ret;
}

static int agent_app_bind_cloud(void *iot_handle)
{
    qm_agent_config_t config;
    qm_audio_control_t *control;
    qm_audio_stream_format_t format;
    int ret;

    if (s_agent != NULL) {
        return QM_EOK;
    }
    if (iot_handle == NULL) {
        return -QM_EINVAL;
    }

    control = voice_get_control();
    if (control == NULL) {
        QM_LOGE(LOG_TAG, "bind failed: voice audio is null");
        return -QM_EINIT;
    }

    ret = qm_audio_get_input_stream_format(&format);
    if (ret != QM_EOK) {
        QM_LOGE(LOG_TAG, "get input format failed ret=%d", ret);
        return ret;
    }
    QM_LOGI(LOG_TAG, "voice uplink opus rate=%u ch=%u",
            (unsigned)format.pcm.sample_rate_hz,
            (unsigned)format.pcm.channels);

    ret = register_agent_events();
    if (ret != QM_EOK) {
        QM_LOGE(LOG_TAG, "event register failed ret=%d", ret);
        return ret;
    }

    qm_memset(&config, 0, sizeof(config));
    config.transport.type = QM_AGENT_TRANSPORT_AGORA;
    config.audio.control = control;
    config.audio.capture_enabled = QM_TRUE;
    /*
     * 跟设备对外格式一致：按包收 Opus，包长不固定。芯片 PCM 的编解码在设备里。
     * 零下行格式表示喇叭也走这份 Opus，设备再解成 PCM。
     */
    config.audio.uplink_format.codec = QM_AGENT_AUDIO_CODEC_OPUS;
    config.audio.uplink_format.data_type = QM_AGENT_AUDIO_CODEC_OPUS;
    config.audio.uplink_format.sample_rate = format.pcm.sample_rate_hz;
    config.audio.uplink_format.channel_num = format.pcm.channels;
    config.audio.uplink_format.bits_per_sample = 16;
    config.audio.uplink_format.frame_ms = (uint16_t)format.packet_duration_ms;
    config.audio.uplink_format.framing = format.packet_bytes == 0 ?
        QM_AGENT_AUDIO_FRAMING_OPUS_PACKET : QM_AGENT_AUDIO_FRAMING_OPUS_CBR;
    config.audio.uplink_format.packet_bytes = format.packet_bytes;
    /*
     * VB701N 的 0x0201 会把喇叭一起停。
     * 对话期间用 KEEP，TTS 下行时不要把麦停掉。
     */
    config.transport_capture_policy = QM_AGENT_CAPTURE_POLICY_KEEP;
    qm_agent_config_init_defaults(&config);
    /* app_id / channel / token / license / uid 由 qm_agent 从鉴权回包填入。 */
    config.transport.data.agora.audio_enable = QM_TRUE;
    config.transport.data.agora.video_enable = QM_FALSE;
    config.iot_handle = iot_handle;

    s_agent = qm_agent_create(&config);
    if (s_agent == NULL) {
        QM_LOGE(LOG_TAG, "qm_agent_create failed");
        return -QM_EINIT;
    }
    QM_LOGI(LOG_TAG, "session created state=%s",
            life_name(qm_agent_get_state(s_agent)));
    agent_sync_upload();
    return QM_EOK;
}

static void agent_on_cloud_connected(void)
{
    s_cloud_connected = 1;
    if (s_agent == NULL) {
        return;
    }
    if (qm_agent_network_update(s_agent, QM_AGENT_NETWORK_UP) != QM_EOK) {
        QM_LOGW(LOG_TAG, "network up failed");
    }
}

static void agent_on_cloud_disconnected(void)
{
    int ret;

    s_cloud_connected = 0;
    s_agent_started = 0;
    s_session_idle = 1U;
    s_dialog_state = QM_AGENT_DIALOG_STATE_NONE;
    agent_idle_timer_stop();
    abort_tts_wait();
    if (s_agent == NULL) {
        return;
    }
    (void)qm_agent_network_update(s_agent, QM_AGENT_NETWORK_DOWN);
    ret = qm_agent_stop(s_agent);
    QM_LOGI(LOG_TAG, "qm_agent_stop ret=%d state=%s",
            ret, life_name(qm_agent_get_state(s_agent)));
}

static void on_cloud_event(ljyd_cloud_event_t event, void *iot_handle, void *userdata)
{
    (void)userdata;
    (void)iot_handle;
    if (event == LJYD_CLOUD_EVENT_CONNECTED) {
        agent_on_cloud_connected();
        return;
    }
    if (event == LJYD_CLOUD_EVENT_DISCONNECTED) {
        agent_on_cloud_disconnected();
    }
}

/* 只投递本地静默（关麦上行），不退出会话。 */
int agent_app_leave(void)
{
    if (s_agent == NULL) {
        return -QM_EINVAL;
    }
    if (!s_worker_ready) {
        return -QM_EINIT;
    }
    abort_tts_wait();
    s_pending_idle = AGENT_IDLE_REQUEST;
    (void)qm_sem_signal(&s_worker_sem);
    QM_LOGI(LOG_TAG, "leave requested, local silence only");
    return QM_EOK;
}

int agent_app_is_active(void)
{
    return (s_agent_started != 0) ? 1 : 0;
}

int agent_app_is_cloud_connected(void)
{
    return (s_cloud_connected != 0 && s_agent != NULL) ? 1 : 0;
}

int agent_app_is_corpus_ready(void)
{
    return (s_cloud_connected != 0 && s_agent != NULL &&
            s_agent->auth.helper != NULL && s_agent->auth.has_auth) ? 1 : 0;
}

int agent_app_is_uplink_enabled(void)
{
    return (s_agent != NULL &&
            qm_agent_audio_engine_upload_allowed(s_agent)) ? 1 : 0;
}

int agent_app_play_local_audio(const void *data, uint32_t len)
{
    qm_audio_control_t *control = NULL;
    qm_audio_control_play_request_t request;
    qm_audio_operation_id_t operation = 0;
    int ret;

    if (data == NULL || len == 0U) {
        return -QM_EINVAL;
    }
    if (!voice_audio_ready()) {
        return -QM_EINIT;
    }

    ret = qm_audio_control_create(&control);
    if (ret != QM_EOK || control == NULL) {
        return ret != QM_EOK ? ret : -QM_EINIT;
    }

    qm_memset(&request, 0, sizeof(request));
    request.source.type = QM_AUDIO_SOURCE_MEMORY;
    request.source.value.memory.data = data;
    request.source.value.memory.size = len;
    request.codec.codec = QM_AUDIO_CODEC_OPUS;
    request.codec.framing = QM_AUDIO_CODEC_FRAMING_STREAM;
    request.codec.packet_duration_ms = 20;
    request.codec.pcm.sample_rate_hz = 16000;
    request.codec.pcm.channels = 1;
    request.codec.pcm.sample = QM_AUDIO_PCM_S16;
    request.priority = QM_AUDIO_PRIORITY_HIGH;
    request.admission = QM_AUDIO_ADMISSION_PREEMPT_LOWER;
    request.admission_timeout_ms = 800;
    ret = qm_audio_control_play(control, &request, &operation);
    if (ret == QM_EOK) {
        ret = qm_audio_control_wait(control, operation, 3000);
        (void)qm_audio_control_release(control, operation, 1000);
    }
    (void)qm_audio_control_shutdown(control, 1000);
    (void)qm_audio_control_destroy(control);
    QM_LOGI(LOG_TAG, "local prompt len=%u ret=%d", (unsigned)len, ret);
    return ret;
}

static void drain_tts_complete_sem(void)
{
    if (!s_tts_complete_sem_ready) {
        return;
    }
    while (qm_sem_wait(&s_tts_complete_sem, QM_NO_WAIT) == QM_EOK) {
    }
}

static void abort_tts_wait(void)
{
    if (!s_waiting_tts_complete) {
        return;
    }
    s_tts_wait_aborted = 1U;
    if (s_tts_complete_sem_ready) {
        (void)qm_sem_signal(&s_tts_complete_sem);
    }
}

/* 上行使能的唯一决策点。 */
static void agent_sync_upload(void)
{
    qm_bool allow;

    if (s_agent == NULL || !voice_audio_ready()) {
        return;
    }
    allow = (qm_bool)(!s_resource_active && !s_session_idle &&
                      s_cloud_connected && s_agent_started);
    qm_agent_set_upload_enabled(s_agent, allow);
}

int agent_app_set_resource_mode(qm_bool active)
{
    if (!voice_audio_ready()) {
        return -QM_EINIT;
    }
    s_resource_active = active ? 1U : 0U;
    agent_sync_upload();
    return QM_EOK;
}

int agent_app_abort_output(void)
{
    qm_agent_event_t *event;
    int ret = QM_EOK;

    /* Prevent an interrupt-generated silent state from closing this reply. */
    if (s_waiting_tts_complete) {
        s_tts_wait_aborted = 1U;
    }
    if (s_agent != NULL) {
        ret = qm_agent_interrupt(s_agent);
        if (ret == -QM_ENOSYS) {
            /*
             * Agora has no local interrupt implementation. qm_agent still
             * closes stream admission while attempting the unsupported
             * interrupt; replay its normalized abort on qm_agent_ctl so the
             * next downlink can reopen admission without touching qdev state
             * from this application thread.
             */
            event = (qm_agent_event_t *)qm_malloc(sizeof(*event));
            if (event == NULL) {
                QM_LOGW(LOG_TAG, "local interrupt reopen alloc failed");
            } else {
                qm_memset(event, 0, sizeof(*event));
                event->id = QM_AGENT_EVENT_AGENT_ABORTED;
                event->source = QM_AGENT_EVENT_SOURCE_TRANSPORT;
                event->code = -QM_ENOSYS;
                if (qm_agent_control_post_event(s_agent, event) == QM_EOK) {
                    QM_LOGI(LOG_TAG, "local interrupt queued audio reopen");
                } else {
                    QM_LOGW(LOG_TAG, "local interrupt audio reopen post failed");
                }
            }
        }
    }
    abort_tts_wait();
    QM_LOGI(LOG_TAG, "abort output ret=%d", ret);
    return ret;
}

static const char *corpus_host_prefix(void)
{
    switch (qm_iot_dynreg_env_get()) {
        case QM_IOT_DYNREG_ENV_TEST:
            return "api-test";
        case QM_IOT_DYNREG_ENV_PROD:
            return "api";
        case QM_IOT_DYNREG_ENV_DEV:
        default:
            return "api-dev";
    }
}

static int get_agent_auth_info(qm_agent_auth_info_t *info)
{
    int ret;

    if (s_agent == NULL || info == NULL) {
        return -QM_EINVAL;
    }
    qm_memset(info, 0, sizeof(*info));
    if (s_agent->auth.helper == NULL || !s_agent->auth.has_auth) {
        return -QM_ENOENT;
    }
    ret = qm_agent_auth_get_token(s_agent->auth.helper, info);
    return ret;
}

int agent_app_user_corpus(const char *text)
{
    qm_agent_auth_info_t auth = {0};
    qm_http_client_request_t request = {0};
    qm_http_client_response_t response = {0};
    qm_http_header_t header;
    cJSON *root;
    char url[AGENT_CORPUS_URL_MAX];
    char *body;
    int ret;

    if (text == NULL || text[0] == '\0') {
        return -QM_EINVAL;
    }
    if (!s_cloud_connected || s_agent == NULL) {
        return -QM_EBUSY;
    }
    ret = get_agent_auth_info(&auth);
    if (ret != QM_EOK || auth.ljyd.token == NULL || auth.ljyd.token[0] == '\0') {
        if (ret == QM_EOK) {
            ret = -QM_ENOENT;
        }
        QM_LOGW(LOG_TAG, "user corpus auth unavailable ret=%d", ret);
        qm_agent_auth_info_deinit(&auth);
        return ret;
    }

    root = cJSON_CreateObject();
    if (root == NULL || !cJSON_AddStringToObject(root, "content", text)) {
        cJSON_Delete(root);
        qm_agent_auth_info_deinit(&auth);
        return -QM_ENOMEM;
    }
    body = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (body == NULL) {
        qm_agent_auth_info_deinit(&auth);
        return -QM_ENOMEM;
    }
    ret = qm_snprintf(url, sizeof(url),
                      "https://%s.ljyd.cn/agent-device/agent/sendSpeakRequest",
                      corpus_host_prefix());
    if (ret <= 0 || ret >= (int)sizeof(url)) {
        cJSON_free(body);
        qm_agent_auth_info_deinit(&auth);
        return -QM_EFULL;
    }

    ret = wait_agent_audio_idle();
    if (ret != QM_EOK) {
        cJSON_free(body);
        qm_agent_auth_info_deinit(&auth);
        return ret;
    }

    drain_tts_complete_sem();
    s_tts_wait_aborted = 0U;
    s_tts_text_seen = 0U;
    s_tts_speaking_seen = 0U;
    s_tts_playback_started = 0U;
    s_tts_playback_failed = 0U;
    s_tts_playback_error = QM_EOK;
    s_tts_silent_seen = 0U;
    s_tts_input_complete_posted = 0U;
    s_waiting_tts_complete = 1U;
    header.name = "Authorization";
    header.value = auth.ljyd.token;
    request.method = QM_HTTP_POST;
    request.url = url;
    request.body = body;
    request.body_len = (int)qm_strlen(body);
    request.content_type = "application/json";
    request.headers = &header;
    request.header_count = 1;
    request.timeout_ms = AGENT_CORPUS_TIMEOUT_MS;
    QM_LOGI(LOG_TAG, "user corpus request url=%s text_len=%u",
            url, (unsigned)qm_strlen(text));
    ret = qm_http_client_execute(&request, &response);
    if (ret == QM_EOK && response.status_code != 200) {
        ret = -QM_EIO;
    }
    if (ret != QM_EOK) {
        s_waiting_tts_complete = 0U;
        s_tts_text_seen = 0U;
        s_tts_speaking_seen = 0U;
        s_tts_playback_started = 0U;
        s_tts_playback_failed = 0U;
        s_tts_playback_error = QM_EOK;
        s_tts_silent_seen = 0U;
        s_tts_input_complete_posted = 0U;
    }
    QM_LOGI(LOG_TAG, "user corpus response ret=%d status=%d",
            ret, response.status_code);
    cJSON_free(body);
    qm_agent_auth_info_deinit(&auth);
    return ret;
}

int agent_app_wait_tts_complete(uint32_t timeout_ms)
{
    int ret;
    int playback_error;
    qm_bool aborted;
    qm_bool playback_failed;

    if (!s_tts_complete_sem_ready || !s_waiting_tts_complete) {
        return -QM_EINVAL;
    }
    ret = qm_sem_wait(&s_tts_complete_sem, timeout_ms);
    aborted = s_tts_wait_aborted ? QM_TRUE : QM_FALSE;
    playback_failed = s_tts_playback_failed ? QM_TRUE : QM_FALSE;
    playback_error = s_tts_playback_error;
    if (s_tts_playback_failed) {
        QM_LOGW(LOG_TAG, "tts playback failed while waiting code=%d",
                (int)s_tts_playback_error);
    }
    if (ret != QM_EOK && !aborted) {
        QM_LOGW(LOG_TAG,
                "wait tts playback complete timeout=%u text=%u speaking=%u started=%u silent=%u posted=%u",
                (unsigned)timeout_ms,
                (unsigned)s_tts_text_seen,
                (unsigned)s_tts_speaking_seen,
                (unsigned)s_tts_playback_started,
                (unsigned)s_tts_silent_seen,
                (unsigned)s_tts_input_complete_posted);
    }
    s_waiting_tts_complete = 0U;
    s_tts_wait_aborted = 0U;
    s_tts_text_seen = 0U;
    s_tts_speaking_seen = 0U;
    s_tts_playback_started = 0U;
    s_tts_playback_failed = 0U;
    s_tts_playback_error = QM_EOK;
    s_tts_silent_seen = 0U;
    s_tts_input_complete_posted = 0U;
    if (aborted) {
        return -QM_EINTR;
    }
    if (playback_failed) {
        /* A failed terminal event is emitted only after qdev has finished
         * cleaning the TTS operation. Keep this request alive so a transient
         * guide-word failure cannot drop the actual resource playback. */
        QM_LOGW(LOG_TAG,
                "tts playback ended with error code=%d; continue resource handoff",
                playback_error);
        return QM_EOK;
    }
    if (ret != QM_EOK) {
        return -QM_ETIMEOUT;
    }
    return QM_EOK;
}

#define AGENT_WORK_TASK_STACK  6144
#define AGENT_WORK_TASK_PRIO   18

static void agent_handle_wakeup(void)
{
    qm_agent_state_t state;
    int ret;

    agent_idle_timer_stop();
    if (s_session_idle) {
        s_session_idle = 0U;
        agent_sync_upload();
        QM_LOGI(LOG_TAG, "wakeup resumes uplink");
    }

    /* A wake word always takes ownership back from active output. */
#if defined(CONFIG_LJYD_PLAYBACK_SUPPORT) && CONFIG_LJYD_PLAYBACK_SUPPORT
    (void)playback_stop();
#endif

    if (s_agent == NULL || !s_cloud_connected) {
        QM_LOGI(LOG_TAG, "wakeup ignored, cloud=%u agent=%p",
                (unsigned)s_cloud_connected, (void *)s_agent);
        return;
    }

    state = qm_agent_get_state(s_agent);
    if (agent_state_is_active(state)) {
        (void)agent_app_abort_output();
        s_agent_started = 1;
        agent_session_touch();
        return;
    }

    ret = qm_agent_start(s_agent);
    QM_LOGI(LOG_TAG, "qm_agent_start ret=%d state=%s",
            ret, life_name(qm_agent_get_state(s_agent)));
    s_agent_started = (ret == QM_EOK) ? 1U : 0U;
    if (s_agent_started) {
        agent_sync_upload();
        agent_session_touch();
    }
}

/* 思考/说话中不静默，避免把正在生成的回复截断。 */
static void agent_handle_idle_silence(void)
{
    if (s_agent == NULL || !s_cloud_connected || !s_agent_started ||
        s_session_idle ||
        s_dialog_state == QM_AGENT_DIALOG_STATE_THINKING ||
        s_dialog_state == QM_AGENT_DIALOG_STATE_SPEAKING) {
        return;
    }
    s_session_idle = 1U;
    agent_sync_upload();
    QM_LOGI(LOG_TAG, "idle silence, uplink off");
}

static void agent_worker_task(void *arg)
{
    (void)arg;

    for (;;) {
        if (qm_sem_wait(&s_worker_sem, QM_WAIT_FOREVER) != QM_EOK) {
            continue;
        }
        if (s_pending_idle != AGENT_IDLE_NONE) {
            s_pending_idle = AGENT_IDLE_NONE;
            agent_handle_idle_silence();
            continue;
        }
        agent_handle_wakeup();
    }
}

/* 运行在 audio_event 任务：只投递，不做任何阻塞调用。 */
static void on_wakeup(void)
{
    if (!s_worker_ready) {
        return;
    }
    (void)qm_sem_signal(&s_worker_sem);
}

int agent_app_init(void *iot_handle)
{
    int ret;

    if (!s_tts_complete_sem_ready) {
        ret = qm_sem_new(&s_tts_complete_sem, 0);
        if (ret != QM_EOK || !qm_sem_is_valid(&s_tts_complete_sem)) {
            return -QM_ENOMEM;
        }
        s_tts_complete_sem_ready = 1U;
    }
    if (!s_worker_ready) {
        ret = qm_sem_new(&s_worker_sem, 0);
        if (ret != QM_EOK || !qm_sem_is_valid(&s_worker_sem)) {
            return -QM_ENOMEM;
        }
        if (qm_task_new(&s_worker_task, "agent_work", agent_worker_task, NULL,
                        AGENT_WORK_TASK_STACK, AGENT_WORK_TASK_PRIO) != 0) {
            (void)qm_sem_free(&s_worker_sem);
            return -QM_EIO;
        }
        s_worker_ready = 1U;
    }
    ret = agent_app_bind_cloud(iot_handle);
    if (ret != QM_EOK) {
        return ret;
    }
    ljyd_cloud_set_event_cb(on_cloud_event, NULL);
    voice_set_wakeup_cb(on_wakeup);
    return QM_EOK;
}
