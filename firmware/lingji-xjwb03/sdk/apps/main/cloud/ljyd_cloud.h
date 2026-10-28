#ifndef LJYD_CLOUD_H
#define LJYD_CLOUD_H

#include "qm_spec_api.h"
#include "qm_config.h"

/* Self-test never uses the SDK example credentials. Cloud builds read a
 * project-local ignored header so the secret stays out of compiler args. */
#if defined(CONFIG_NODEHEXA_VOICE_SELFTEST) && CONFIG_NODEHEXA_VOICE_SELFTEST
#ifndef CONFIG_XJIANG_CLOUD_PID
#define CONFIG_XJIANG_CLOUD_PID 0
#endif
#ifndef CONFIG_XJIANG_CLOUD_SECERT
#define CONFIG_XJIANG_CLOUD_SECERT ""
#endif
#else
#include "../../../../project_identity.local.h"
#ifndef CONFIG_XJIANG_CLOUD_PID
#error "Set this project's XJIANG_CLOUD_PID in project_identity.local.h"
#endif
#if CONFIG_XJIANG_CLOUD_PID <= 0
#error "The project product PID must be positive"
#endif
#ifndef CONFIG_XJIANG_CLOUD_SECERT
#error "Set this project's XJIANG_CLOUD_SECERT in project_identity.local.h"
#endif
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    LJYD_CLOUD_EVENT_CONNECTED = 0,
    LJYD_CLOUD_EVENT_DISCONNECTED,
} ljyd_cloud_event_t;

typedef void (*ljyd_cloud_event_cb_t)(ljyd_cloud_event_t event, void *iot_handle, void *userdata);
typedef void (*ljyd_cloud_prop_cb_t)(qm_spec_property_t *property);

int ljyd_cloud_init(void);
void *ljyd_cloud_get_handle(void);
void ljyd_cloud_set_event_cb(ljyd_cloud_event_cb_t cb, void *userdata);
/* 属性下发。不设置则云只打日志。iot_control 在自己的 init 里挂上。 */
void ljyd_cloud_set_prop_cb(ljyd_cloud_prop_cb_t cb);
void ljyd_cloud_on_network_up(void);
void ljyd_cloud_on_network_down(void);
/* 返回 QM_EOK 表示云已接手解绑，等 RESET 事件再清配网。 */
int ljyd_cloud_request_reset(void);

#ifdef __cplusplus
}
#endif

#endif
