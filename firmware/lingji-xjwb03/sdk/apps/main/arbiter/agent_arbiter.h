#ifndef AGENT_ARBITER_H
#define AGENT_ARBITER_H

#include <stdint.h>
#include "qm_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* 竞争同一音频通路与对话会话的来源。 */
typedef enum {
    AGENT_ARBITER_OWNER_BOOT_SOUND = 0,
    AGENT_ARBITER_OWNER_ALARM,
    AGENT_ARBITER_OWNER_PLAYBACK,
    AGENT_ARBITER_OWNER_DIALOG,
    AGENT_ARBITER_OWNER_VISION,
    AGENT_ARBITER_OWNER_MAX
} agent_arbiter_owner_t;

/* 优先级，数值越大越不可被抢占。 */
typedef enum {
    AGENT_ARBITER_PRIO_LOW = 0,
    AGENT_ARBITER_PRIO_NORMAL,
    AGENT_ARBITER_PRIO_HIGH,
    AGENT_ARBITER_PRIO_CRITICAL
} agent_arbiter_prio_t;

/* 初始化，创建内部互斥锁，须在任何申请之前调用。 */
int agent_arbiter_init(void);

/*
 * 申请通路：首个持有者执行让位（关麦克风上行、停对端输出），
 * 同一来源可重复申请，须成对释放。返回 QM_EOK，或 -QM_EBUSY（已有同级或更高优先级在占用）。
 */
int agent_arbiter_request(agent_arbiter_owner_t owner, agent_arbiter_prio_t prio);

/* 释放通路：最后一个持有者释放时恢复被让位的来源；被接管过的来源释放时忽略。 */
int agent_arbiter_release(agent_arbiter_owner_t owner);

/* 资源播放结束上报，boot_sound 与 playback 播完时调用。 */
void agent_arbiter_notify_playback_done(agent_arbiter_owner_t owner);

/* 对话活动上报，用于本地静默超时计时，尚未接入。 */
void agent_arbiter_notify_dialog_activity(void);

/* 返回 1 表示当前有来源占用通路。 */
int agent_arbiter_is_occupied(void);

#ifdef __cplusplus
}
#endif

#endif
