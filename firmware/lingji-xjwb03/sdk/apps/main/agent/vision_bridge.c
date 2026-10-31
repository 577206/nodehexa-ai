#include "vision_bridge.h"

#include "agent_app.h"
#include "agent_arbiter.h"
#include "qm_cli.h"
#include "qm_errno.h"
#include "qm_log.h"

#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/idf_additions.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "mbedtls/base64.h"

#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define LOG_TAG "vision_bridge"
#define VISION_TEXT_MAX_BYTES 160U
#define VISION_ASR_MAX_BYTES 180U
#define VISION_WORKER_STACK (12 * 1024)

typedef struct {
    char text[VISION_TEXT_MAX_BYTES + 1U];
    bool feedback;
} vision_request_t;

static QueueHandle_t s_queue;
static TaskHandle_t s_worker;
static atomic_bool s_busy = ATOMIC_VAR_INIT(false);
static portMUX_TYPE s_asr_lock = portMUX_INITIALIZER_UNLOCKED;
static char s_last_asr[VISION_ASR_MAX_BYTES + 1U];
static uint32_t s_last_asr_sequence;

uint32_t vision_bridge_last_asr(char *text, size_t capacity)
{
    uint32_t sequence;
    if (text == NULL || capacity == 0U) return 0U;
    portENTER_CRITICAL(&s_asr_lock);
    snprintf(text, capacity, "%s", s_last_asr);
    sequence = s_last_asr_sequence;
    portEXIT_CRITICAL(&s_asr_lock);
    return sequence;
}

bool vision_bridge_cloud_connected(void) { return agent_app_is_cloud_connected(); }
bool vision_bridge_active(void) { return agent_app_is_active(); }
bool vision_bridge_uplink_enabled(void) { return agent_app_is_uplink_enabled(); }
bool vision_bridge_corpus_ready(void) { return agent_app_is_corpus_ready(); }

void vision_bridge_on_asr(const char *text, int truncated)
{
    unsigned char encoded[256];
    size_t encoded_len = 0U;
    size_t len;

    if (s_queue == NULL || text == NULL || truncated) {
        return;
    }
    len = strlen(text);
    if (len == 0U || len > VISION_ASR_MAX_BYTES ||
        mbedtls_base64_encode(encoded, sizeof(encoded) - 1U, &encoded_len,
                              (const unsigned char *)text, len) != 0) {
        return;
    }
    encoded[encoded_len] = '\0';
    portENTER_CRITICAL(&s_asr_lock);
    memcpy(s_last_asr, text, len + 1U);
    ++s_last_asr_sequence;
    portEXIT_CRITICAL(&s_asr_lock);
    qm_cli_printf("VISION-ASR %s\r\n", encoded);
}

bool vision_bridge_submit(const char *text, size_t length)
{
    vision_request_t *item;
    if (text == NULL || length == 0U || length > VISION_TEXT_MAX_BYTES ||
        s_queue == NULL || !agent_app_is_cloud_connected()) return false;
    for (size_t i = 0; i < length; ++i) {
        if ((unsigned char)text[i] < 0x20U || text[i] == 0x7f) return false;
    }
    if (atomic_exchange(&s_busy, true)) return false;
    item = heap_caps_malloc(sizeof(*item), MALLOC_CAP_8BIT);
    if (item == NULL) {
        atomic_store(&s_busy, false);
        return false;
    }
    memcpy(item->text, text, length);
    item->text[length] = '\0';
    item->feedback = false;
    if (xQueueSend(s_queue, &item, 0) != pdTRUE) {
        heap_caps_free(item);
        atomic_store(&s_busy, false);
        return false;
    }
    return true;
}

static void vision_worker(void *arg)
{
    (void)arg;
    for (;;) {
        vision_request_t *item = NULL;
        char corpus[512];
        int ret;
        if (xQueueReceive(s_queue, &item, portMAX_DELAY) != pdTRUE || item == NULL) {
            continue;
        }
        /* sendSpeakRequest plays the content as speech. Only pass the final
         * user-facing answer; instructions here would be read aloud. */
        ret = snprintf(corpus, sizeof(corpus), "%s", item->text);
        heap_caps_free(item);
        if (ret <= 0 || ret >= (int)sizeof(corpus)) {
            QM_LOGW(LOG_TAG, "VISION-ERROR text too long");
            atomic_store(&s_busy, false);
            continue;
        }
        for (unsigned attempt = 0; attempt < 12 && !agent_app_is_corpus_ready(); ++attempt) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
        if (!agent_app_is_corpus_ready()) {
            QM_LOGW(LOG_TAG, "VISION-ERROR agent auth unavailable");
            atomic_store(&s_busy, false);
            continue;
        }
        ret = agent_arbiter_request(AGENT_ARBITER_OWNER_VISION,
                                    AGENT_ARBITER_PRIO_NORMAL);
        if (ret != 0) {
            QM_LOGW(LOG_TAG, "VISION-ERROR audio busy ret=%d", ret);
            atomic_store(&s_busy, false);
            continue;
        }
        /* A token refresh may race the request. Retry only the definite
         * auth-unavailable result; other failures may already be delivered. */
        for (unsigned attempt = 0; attempt < 6; ++attempt) {
            ret = agent_app_user_corpus(corpus);
            if (ret != -QM_ENOENT) break;
            vTaskDelay(pdMS_TO_TICKS(2000));
        }
        if (ret == 0) {
            QM_LOGI(LOG_TAG, "VISION-SENT");
            ret = agent_app_wait_tts_complete(30000U);
        }
        if (ret == 0) {
            QM_LOGI(LOG_TAG, "VISION-DONE");
        } else {
            QM_LOGW(LOG_TAG, "VISION-ERROR agent ret=%d", ret);
        }
        (void)agent_arbiter_release(AGENT_ARBITER_OWNER_VISION);
        atomic_store(&s_busy, false);
    }
}

static void vision_cli_command(char *out, int out_len, int argc, char **argv)
{
    vision_request_t *item;
    size_t decoded = 0;
    int ret;
    const bool feedback = argc > 0 && strcmp(argv[0], "feedback") == 0;

    if (argc == 2 && strcmp(argv[1], "ping") == 0) {
        snprintf(out, out_len, "%s\r\n",
                 s_queue != NULL && agent_app_is_cloud_connected() ?
                 "VISION-READY" : "VISION-UNAVAILABLE");
        return;
    }
    if (argc == 2 && strcmp(argv[1], "status") == 0) {
        snprintf(out, out_len, "VISION-STATUS cloud=%d active=%d uplink=%d auth=%d\r\n",
                 agent_app_is_cloud_connected(), agent_app_is_active(),
                 agent_app_is_uplink_enabled(), agent_app_is_corpus_ready());
        return;
    }
    if (argc != 2 || (strcmp(argv[0], "vision") != 0 && !feedback)) {
        snprintf(out, out_len, "usage: vision|feedback <base64-utf8>\r\n");
        return;
    }
    if (s_queue == NULL || !agent_app_is_cloud_connected()) {
        snprintf(out, out_len, "VISION-UNAVAILABLE\r\n");
        return;
    }
    if (atomic_exchange(&s_busy, true)) {
        snprintf(out, out_len, "VISION-BUSY\r\n");
        return;
    }
    item = heap_caps_malloc(sizeof(*item), MALLOC_CAP_8BIT);
    if (item == NULL) {
        atomic_store(&s_busy, false);
        snprintf(out, out_len, "VISION-ERROR memory\r\n");
        return;
    }
    ret = mbedtls_base64_decode((unsigned char *)item->text,
                                VISION_TEXT_MAX_BYTES, &decoded,
                                (const unsigned char *)argv[1], strlen(argv[1]));
    if (ret != 0 || decoded == 0 || decoded > VISION_TEXT_MAX_BYTES ||
        memchr(item->text, '\0', decoded) != NULL) {
        heap_caps_free(item);
        atomic_store(&s_busy, false);
        snprintf(out, out_len, "VISION-ERROR invalid text\r\n");
        return;
    }
    for (size_t i = 0; i < decoded; ++i) {
        if ((unsigned char)item->text[i] < 0x20U || item->text[i] == 0x7f) {
            heap_caps_free(item);
            atomic_store(&s_busy, false);
            snprintf(out, out_len, "VISION-ERROR control character\r\n");
            return;
        }
    }
    item->text[decoded] = '\0';
    item->feedback = feedback;
    if (xQueueSend(s_queue, &item, 0) != pdTRUE) {
        heap_caps_free(item);
        atomic_store(&s_busy, false);
        snprintf(out, out_len, "VISION-BUSY\r\n");
        return;
    }
    snprintf(out, out_len, "%s-QUEUED\r\n", feedback ? "FEEDBACK" : "VISION");
}

static const struct qm_cli_command s_vision_cli = {
    .name = "vision",
    .help = "vision <base64-utf8>: send one visual description to voice Agent",
    .function = vision_cli_command,
};

static const struct qm_cli_command s_feedback_cli = {
    .name = "feedback",
    .help = "feedback <base64-utf8>: speak one confirmed robot status",
    .function = vision_cli_command,
};

int vision_bridge_init(void)
{
    if (s_queue != NULL) {
        return 0;
    }
    s_queue = xQueueCreate(1, sizeof(vision_request_t *));
    if (s_queue == NULL) {
        return -1;
    }
    if (xTaskCreatePinnedToCoreWithCaps(vision_worker, "vision_link",
                                        VISION_WORKER_STACK, NULL, 10,
                                        &s_worker, 1,
                                        MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT) != pdPASS) {
        vQueueDelete(s_queue);
        s_queue = NULL;
        return -1;
    }
    if (qm_cli_register_command(&s_vision_cli) != 0) {
        vTaskDelete(s_worker);
        s_worker = NULL;
        vQueueDelete(s_queue);
        s_queue = NULL;
        return -1;
    }
    if (qm_cli_register_command(&s_feedback_cli) != 0) {
        qm_cli_unregister_command(&s_vision_cli);
        vTaskDelete(s_worker);
        s_worker = NULL;
        vQueueDelete(s_queue);
        s_queue = NULL;
        return -1;
    }
    QM_LOGI(LOG_TAG, "vision serial bridge ready");
    return 0;
}
