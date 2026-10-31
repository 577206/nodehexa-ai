#include "wifi_bridge.h"
#include "../eyes/eyes.h"

#include "bsp_camera.h"
#include "robot_link.h"
#include "vision_bridge.h"
#include "agent_app.h"
#include "direct_audio.h"
#include "qm.h"
#include "qm_log.h"

#include "cJSON.h"
#include "esp_heap_caps.h"
#include "esp_http_server.h"
#include "esp_netif.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Generated locally; never commit or print the bridge token. */
#include "../../../../secrets.local.h"

#ifndef CONFIG_LINGXI_BRIDGE_TOKEN
#error "Create secrets.local.h with CONFIG_LINGXI_BRIDGE_TOKEN before building"
#endif

#define LOG_TAG "wifi_bridge"
#define BRIDGE_PORT 8766
#define MAX_POST_BYTES 384

static httpd_handle_t s_server;

static esp_err_t send_error(httpd_req_t *req, const char *status, const char *message)
{
    httpd_resp_set_status(req, status);
    httpd_resp_set_type(req, "text/plain; charset=utf-8");
    return httpd_resp_send(req, message, HTTPD_RESP_USE_STRLEN);
}

static bool authorized(httpd_req_t *req)
{
    static const char expected[] = CONFIG_LINGXI_BRIDGE_TOKEN;
    char received[sizeof(expected)];
    unsigned difference = 0U;
    const size_t length = httpd_req_get_hdr_value_len(req, "X-Lingxi-Token");
    if (length != sizeof(expected) - 1U || length < 32U ||
        httpd_req_get_hdr_value_str(req, "X-Lingxi-Token", received,
                                     sizeof(received)) != ESP_OK) {
        httpd_resp_send_err(req, HTTPD_403_FORBIDDEN, "Bridge token required");
        return false;
    }
    for (size_t i = 0; i < length; ++i)
        difference |= (unsigned)(received[i] ^ expected[i]);
    if (difference != 0U) {
        httpd_resp_send_err(req, HTTPD_403_FORBIDDEN, "Invalid bridge token");
        return false;
    }
    return true;
}

static esp_err_t send_json(httpd_req_t *req, cJSON *object, const char *status)
{
    char *body = object != NULL ? cJSON_PrintUnformatted(object) : NULL;
    if (object != NULL) cJSON_Delete(object);
    if (body == NULL) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "JSON memory error");
        return ESP_FAIL;
    }
    httpd_resp_set_status(req, status);
    httpd_resp_set_type(req, "application/json; charset=utf-8");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    const esp_err_t result = httpd_resp_send(req, body, HTTPD_RESP_USE_STRLEN);
    cJSON_free(body);
    return result;
}

static esp_err_t status_get(httpd_req_t *req)
{
    if (!authorized(req)) return ESP_OK;
    char asr[181];
    const uint32_t asr_sequence = vision_bridge_last_asr(asr, sizeof(asr));
    const robot_link_snapshot_t robot = robot_link_snapshot();
    cJSON *root = cJSON_CreateObject();
    if (root == NULL) return send_json(req, NULL, "500 Internal Server Error");
    cJSON *eyes=cJSON_AddObjectToObject(root,"eyes");
    if(eyes){
        unsigned mask=eyes_ready_mask();
        cJSON_AddBoolToObject(eyes,"left",mask&1);
        cJSON_AddBoolToObject(eyes,"right",mask&2);
        cJSON_AddNumberToObject(eyes,"mode",eyes_current_mode());
        cJSON_AddNumberToObject(eyes,"contrast",eyes_contrast());
    }
    cJSON_AddNumberToObject(root, "protocol", 1);
    cJSON_AddBoolToObject(root, "directAudio", CONFIG_NODEHEXA_QWEN_DIRECT);
    cJSON_AddNumberToObject(root, "audioState", direct_audio_state());
    cJSON_AddNumberToObject(root, "audioGeneration", direct_audio_generation());
    cJSON_AddNumberToObject(root, "asrSequence", asr_sequence);
    cJSON_AddStringToObject(root, "asrText", asr);
    cJSON_AddBoolToObject(root, "cloud", vision_bridge_cloud_connected());
    cJSON_AddBoolToObject(root, "active", vision_bridge_active());
    cJSON_AddBoolToObject(root, "uplink", vision_bridge_uplink_enabled());
    cJSON_AddBoolToObject(root, "auth", vision_bridge_corpus_ready());
    cJSON_AddBoolToObject(root, "camera", bsp_camera_is_available());
    cJSON *voice = cJSON_AddObjectToObject(root, "voiceDebug");
    if (voice != NULL) {
        cJSON_AddBoolToObject(voice, "mediaConnected",
                              agent_app_is_media_connected());
        cJSON_AddBoolToObject(voice, "ttsWaiting",
                              agent_app_is_tts_waiting());
        cJSON_AddNumberToObject(voice, "dialogState",
                                agent_app_dialog_state());
        cJSON_AddNumberToObject(voice, "errorCount",
                                agent_app_error_count());
    }
    cJSON *memory = cJSON_AddObjectToObject(root, "memory");
    if (memory != NULL) {
        cJSON_AddNumberToObject(memory, "psramFree",
                                heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
        cJSON_AddNumberToObject(memory, "psramLargest",
                                heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM));
        cJSON_AddNumberToObject(memory, "psramMinimum",
                                heap_caps_get_minimum_free_size(MALLOC_CAP_SPIRAM));
    }
    cJSON *link = cJSON_AddObjectToObject(root, "robot");
    if (link != NULL) {
        cJSON_AddNumberToObject(link, "presetVersion", 2);
        cJSON *actions = cJSON_AddArrayToObject(link, "actions");
        if (actions != NULL) {
            for (unsigned i=0;i<robot_link_action_count();i++)
                cJSON_AddItemToArray(actions,cJSON_CreateString(robot_link_action_name(i)));
        }
        cJSON_AddBoolToObject(link, "online", robot.online);
        cJSON_AddBoolToObject(link, "bench", robot.bench);
        cJSON_AddNumberToObject(link, "tx", robot.tx_count);
        cJSON_AddNumberToObject(link, "rx", robot.rx_count);
        cJSON_AddNumberToObject(link, "ackSequence", robot.ack_sequence);
        cJSON_AddStringToObject(link, "ackAction", robot.ack_action);
        cJSON_AddBoolToObject(link, "ackSuccess", robot.ack_success);
    }
    return send_json(req, root, "200 OK");
}

static esp_err_t snapshot_get(httpd_req_t *req)
{
    uint8_t *jpeg = NULL;
    size_t length = 0U;
    if (!authorized(req)) return ESP_OK;
    if (bsp_camera_capture_jpeg(&jpeg, &length) != ESP_OK ||
        jpeg == NULL || length < 4U || length > 256U * 1024U) {
        heap_caps_free(jpeg);
        send_error(req, "503 Service Unavailable", "Camera not ready");
        return ESP_OK;
    }
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    const esp_err_t result = httpd_resp_send(req, (const char *)jpeg, length);
    heap_caps_free(jpeg);
    return result;
}

static cJSON *read_post(httpd_req_t *req)
{
    char body[MAX_POST_BYTES + 1U];
    size_t used = 0U;
    if (req->content_len == 0 || req->content_len > MAX_POST_BYTES) return NULL;
    while (used < req->content_len) {
        const int count = httpd_req_recv(req, body + used, req->content_len - used);
        if (count <= 0) return NULL;
        used += (size_t)count;
    }
    body[used] = '\0';
    return cJSON_ParseWithLength(body, used);
}

static esp_err_t eyes_post(httpd_req_t *req)
{
    if(!authorized(req))return ESP_OK;
    cJSON *body=read_post(req);
    cJSON *mode=cJSON_GetObjectItemCaseSensitive(body,"mode");
    cJSON *duration=cJSON_GetObjectItemCaseSensitive(body,"durationMs");
    cJSON *contrast=cJSON_GetObjectItemCaseSensitive(body,"contrast");
    if(!cJSON_IsObject(body)||cJSON_GetArraySize(body)!=3||
       !cJSON_IsNumber(mode)||mode->valuedouble!=mode->valueint||mode->valueint < -1||mode->valueint>=EYE_MODE_COUNT||
       !cJSON_IsNumber(duration)||duration->valuedouble!=duration->valueint||duration->valueint<100||duration->valueint>10000||
       !cJSON_IsNumber(contrast)||contrast->valuedouble!=contrast->valueint||contrast->valueint<0||contrast->valueint>255){
        cJSON_Delete(body);return send_error(req,"400 Bad Request","Invalid eye controls");
    }
    eyes_control(mode->valueint,duration->valueint,contrast->valueint);
    cJSON_Delete(body);
    cJSON *result=cJSON_CreateObject();cJSON_AddStringToObject(result,"status","queued");
    return send_json(req,result,"202 Accepted");
}

static esp_err_t speak_post(httpd_req_t *req)
{
    if (!authorized(req)) return ESP_OK;
#if CONFIG_NODEHEXA_QWEN_DIRECT
    return send_error(req, "410 Gone", "Use the direct audio transport");
#endif
    cJSON *body = read_post(req);
    const cJSON *value = body != NULL ? cJSON_GetObjectItemCaseSensitive(body, "text") : NULL;
    const char *text = cJSON_IsString(value) ? value->valuestring : NULL;
    const size_t length = text != NULL ? strlen(text) : 0U;
    if (text == NULL || length == 0U || length > 160U ||
        !vision_bridge_submit(text, length)) {
        cJSON_Delete(body);
        send_error(req, "409 Conflict", "Speech unavailable or invalid text");
        return ESP_OK;
    }
    cJSON_Delete(body);
    cJSON *result = cJSON_CreateObject();
    cJSON_AddStringToObject(result, "status", "queued");
    return send_json(req, result, "202 Accepted");
}

static esp_err_t motion_post(httpd_req_t *req)
{
    if (!authorized(req)) return ESP_OK;
    cJSON *body = read_post(req);
    const cJSON *value = body != NULL ? cJSON_GetObjectItemCaseSensitive(body, "action") : NULL;
    const char *action = cJSON_IsString(value) ? value->valuestring : NULL;
    const robot_link_result_t code = robot_link_request_action(action);
    cJSON_Delete(body);
    cJSON *result = cJSON_CreateObject();
    const char *name = code == ROBOT_LINK_QUEUED ? "queued" :
                       code == ROBOT_LINK_OFFLINE ? "offline" :
                       code == ROBOT_LINK_BENCH ? "bench" :
                       code == ROBOT_LINK_BUSY ? "busy" : "invalid";
    cJSON_AddStringToObject(result, "status", name);
    return send_json(req, result, code == ROBOT_LINK_QUEUED ? "202 Accepted" : "409 Conflict");
}

static esp_err_t audio_get(httpd_req_t *req)
{
    if (!authorized(req)) return ESP_OK;
    uint8_t data[3200];
    size_t length = direct_audio_read(data, sizeof(data));
    if (!length) return send_error(req, "503 Service Unavailable", "Direct audio not ready");
    httpd_resp_set_type(req, "application/octet-stream");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    return httpd_resp_send(req, (const char *)data, length);
}

static esp_err_t audio_post(httpd_req_t *req)
{
    if (!authorized(req)) return ESP_OK;
    uint8_t data[3200];
    if (req->content_len < 5 || req->content_len > sizeof(data))
        return send_error(req, "400 Bad Request", "Invalid audio batch");
    size_t used=0;
    while (used<req->content_len) {
        int n=httpd_req_recv(req,(char *)data+used,req->content_len-used);
        if(n<=0) return ESP_FAIL;
        used+=(size_t)n;
    }
    int result=direct_audio_write(data,used);
    if(result) return send_error(req, result==1 ? "409 Conflict" :
                                result==2 ? "429 Too Many Requests" :
                                result==3 ? "400 Bad Request" : "503 Service Unavailable", "Audio batch rejected");
    httpd_resp_set_status(req,"202 Accepted");
    return httpd_resp_send(req,"accepted",8);
}

int wifi_bridge_init(void)
{
    if (s_server != NULL) return 0;
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = BRIDGE_PORT;
    config.stack_size = 8192;
    config.max_uri_handlers = 7;
    config.max_open_sockets = 4;
    config.lru_purge_enable = true;
    config.recv_wait_timeout = 8;
    config.send_wait_timeout = 8;
    if (httpd_start(&s_server, &config) != ESP_OK) return -1;
    const httpd_uri_t handlers[] = {
        {.uri = "/api/eyes", .method = HTTP_POST, .handler = eyes_post},
        {.uri = "/api/audio/up", .method = HTTP_GET, .handler = audio_get},
        {.uri = "/api/audio/down", .method = HTTP_POST, .handler = audio_post},
        {.uri = "/api/status", .method = HTTP_GET, .handler = status_get},
        {.uri = "/api/frame.jpg", .method = HTTP_GET, .handler = snapshot_get},
        {.uri = "/api/speak", .method = HTTP_POST, .handler = speak_post},
        {.uri = "/api/motion", .method = HTTP_POST, .handler = motion_post},
    };
    for (size_t i = 0; i < sizeof(handlers) / sizeof(handlers[0]); ++i) {
        if (httpd_register_uri_handler(s_server, &handlers[i]) != ESP_OK) {
            httpd_stop(s_server);
            s_server = NULL;
            return -1;
        }
    }
    QM_LOGI(LOG_TAG, "authenticated LAN bridge listening on port %u", BRIDGE_PORT);
    return 0;
}
