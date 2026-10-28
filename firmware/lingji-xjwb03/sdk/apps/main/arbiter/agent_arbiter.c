/*
 * 资源让位仲裁层。
 *
 * 资源来源在出声前申请通路、播完释放：首个持有者统一执行让位动作（关麦克风上行、
 * 停对端输出），最后一个持有者释放时恢复。更高优先级来源可接管低优先级持有者，
 * 被接管者随后释放不会误恢复，避免两个来源交叉调用时把让位提前放开。
 *
 * 调用方跨任务（boot_sound 任务、playback 命令任务、qm_work 工作线程），状态用互斥锁
 * 串行化；让位/恢复会阻塞等 qm_agent 控制任务，所以状态在锁内更新、动作在锁外执行。
 */
#include "agent_arbiter.h"
#include "qm.h"
#include "qm_errno.h"
#include "qm_log.h"
#include "qm_string.h"
#include "agent_app.h"

#define LOG_TAG "arb"

typedef struct {
    int owner;        /* 当前持有者，-1 表示空闲 */
    int prio;
    uint16_t depth;   /* 同一来源的嵌套计数 */
    qm_bool yielded;  /* 是否已执行让位动作，需要恢复 */
} agent_arbiter_env_t;

static agent_arbiter_env_t s_arb;
static qm_mutex_t s_lock;
static uint8_t s_lock_ok;

static void arbiter_lock(void)
{
    if (s_lock_ok) {
        qm_mutex_lock(&s_lock, QM_WAIT_FOREVER);
    }
}

static void arbiter_unlock(void)
{
    if (s_lock_ok) {
        qm_mutex_unlock(&s_lock);
    }
}

int agent_arbiter_init(void)
{
    qm_memset(&s_arb, 0, sizeof(s_arb));
    s_arb.owner = -1;
    if (!s_lock_ok) {
        if (qm_mutex_new(&s_lock) != QM_EOK) {
            QM_LOGE(LOG_TAG, "mutex create failed");
            return -QM_ENOMEM;
        }
        s_lock_ok = 1U;
    }
    QM_LOGI(LOG_TAG, "arbiter init");
    return QM_EOK;
}

int agent_arbiter_request(agent_arbiter_owner_t owner, agent_arbiter_prio_t prio)
{
    qm_bool yield = QM_FALSE;

    arbiter_lock();
    if (s_arb.owner == (int)owner) {
        s_arb.depth++;
        arbiter_unlock();
        return QM_EOK;
    }
    if (s_arb.owner >= 0 && (int)prio <= s_arb.prio) {
        QM_LOGW(LOG_TAG, "request owner=%d prio=%d refused, holder owner=%d prio=%d",
                owner, prio, s_arb.owner, s_arb.prio);
        arbiter_unlock();
        return -QM_EBUSY;
    }
    if (s_arb.owner >= 0) {
        QM_LOGW(LOG_TAG, "request owner=%d prio=%d takes over owner=%d prio=%d",
                owner, prio, s_arb.owner, s_arb.prio);
    }

    s_arb.owner = (int)owner;
    s_arb.prio = (int)prio;
    s_arb.depth = 1;
    /* 没有对话会话时不需要让位，只是登记持有关系 */
    if (!s_arb.yielded && agent_app_is_active()) {
        s_arb.yielded = QM_TRUE;
        yield = QM_TRUE;
    }
    arbiter_unlock();

    if (yield) {
        (void)agent_app_set_resource_mode(QM_TRUE);
        (void)agent_app_abort_output();
    }
    QM_LOGI(LOG_TAG, "request owner=%d prio=%d ok", owner, prio);
    return QM_EOK;
}

int agent_arbiter_release(agent_arbiter_owner_t owner)
{
    qm_bool resume = QM_FALSE;

    arbiter_lock();
    if (s_arb.owner != (int)owner) {
        QM_LOGW(LOG_TAG, "release owner=%d ignored, holder owner=%d", owner, s_arb.owner);
        arbiter_unlock();
        return QM_EOK;
    }
    if (s_arb.depth > 1U) {
        s_arb.depth--;
        arbiter_unlock();
        return QM_EOK;
    }

    s_arb.owner = -1;
    s_arb.prio = (int)AGENT_ARBITER_PRIO_LOW;
    s_arb.depth = 0;
    if (s_arb.yielded) {
        s_arb.yielded = QM_FALSE;
        resume = QM_TRUE;
    }
    arbiter_unlock();

    if (resume) {
        (void)agent_app_set_resource_mode(QM_FALSE);
    }
    QM_LOGI(LOG_TAG, "release owner=%d done", owner);
    return QM_EOK;
}

void agent_arbiter_notify_playback_done(agent_arbiter_owner_t owner)
{
    /* 恢复动作由 release 触发，这里只记录事件，后续用于资源排队与续播。 */
    QM_LOGI(LOG_TAG, "playback done owner=%d", owner);
}

void agent_arbiter_notify_dialog_activity(void)
{
}

int agent_arbiter_is_occupied(void)
{
    int occupied;

    arbiter_lock();
    occupied = (s_arb.owner >= 0) ? 1 : 0;
    arbiter_unlock();
    return occupied;
}
