#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool online;
    bool bench;
    uint32_t tx_count;
    uint32_t rx_count;
    uint32_t ack_sequence;
    const char *ack_action;
    bool ack_success;
} robot_link_snapshot_t;

typedef enum {
    ROBOT_LINK_QUEUED,
    ROBOT_LINK_OFFLINE,
    ROBOT_LINK_BENCH,
    ROBOT_LINK_BUSY,
    ROBOT_LINK_INVALID,
} robot_link_result_t;

robot_link_snapshot_t robot_link_snapshot(void);
robot_link_result_t robot_link_request_action(const char *action);
unsigned robot_link_action_count(void);
const char *robot_link_action_name(unsigned index);

/* Start the UART v2 HELLO/heartbeat and bounded preset action link. */
int robot_link_init(void);
