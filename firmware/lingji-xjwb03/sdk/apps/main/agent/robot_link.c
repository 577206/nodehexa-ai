#include "robot_link.h"

#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "qm_cli.h"
#include "qm_log.h"

#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define LOG_TAG "robot_link"
#define LINK_UART UART_NUM_2
#define LINK_TX 17
#define LINK_RX 18
#define LINK_MAX_PAYLOAD 512U
#define LINK_INTERVAL_MS 2000U
#define LINK_OFFLINE_MS 6000U

static atomic_bool s_online = ATOMIC_VAR_INIT(false);
static atomic_bool s_bench = ATOMIC_VAR_INIT(false);
static atomic_uint s_rx_count = ATOMIC_VAR_INIT(0);
static atomic_uint s_tx_count = ATOMIC_VAR_INIT(0);
static uint16_t s_pending_sequence;

static uint16_t crc16(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xffff;
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (unsigned bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000U) ? (uint16_t)((crc << 1) ^ 0x1021U) : (uint16_t)(crc << 1);
        }
    }
    return crc;
}

static void send_probe(uint8_t type, uint16_t sequence)
{
    const char *payload = type == 1 ? "{\"device\":\"lingji\",\"firmware\":\"robot-link-1\"}" : "{}";
    const size_t len = strlen(payload);
    uint8_t frame[96] = {0xa5, 0x4e, 2, type, 0,
                         (uint8_t)sequence, (uint8_t)(sequence >> 8),
                         (uint8_t)len, (uint8_t)(len >> 8)};
    memcpy(frame + 9, payload, len);
    const uint16_t crc = crc16(frame + 2, 7 + len);
    frame[9 + len] = (uint8_t)crc;
    frame[10 + len] = (uint8_t)(crc >> 8);
    if (uart_write_bytes(LINK_UART, frame, 11 + len) == (int)(11 + len)) {
        s_pending_sequence = sequence;
        atomic_fetch_add(&s_tx_count, 1);
    }
}

static void link_task(void *arg)
{
    (void)arg;
    uint8_t frame[LINK_MAX_PAYLOAD + 12U];
    size_t used = 0, total = 0;
    uint16_t sequence = 0;
    TickType_t next_probe = xTaskGetTickCount(), last_reply = 0, last_byte = 0;
    for (;;) {
        uint8_t byte;
        const TickType_t now = xTaskGetTickCount();
        if (used && (now - last_byte) > pdMS_TO_TICKS(250)) used = total = 0;
        if (atomic_load(&s_online) && (now - last_reply) > pdMS_TO_TICKS(LINK_OFFLINE_MS)) {
            atomic_store(&s_online, false);
            atomic_store(&s_bench, false);
            QM_LOGW(LOG_TAG, "NodeHexa offline");
        }
        if ((int32_t)(now - next_probe) >= 0) {
            if (++sequence == 0) ++sequence;
            send_probe(atomic_load(&s_online) ? 5 : 1, sequence);
            next_probe = now + pdMS_TO_TICKS(LINK_INTERVAL_MS);
        }
        if (uart_read_bytes(LINK_UART, &byte, 1, pdMS_TO_TICKS(20)) != 1) continue;
        last_byte = xTaskGetTickCount();
        if (used == 0 && byte != 0xa5) continue;
        if (used == 1 && byte != 0x4e) {
            used = byte == 0xa5 ? 1 : 0;
            continue;
        }
        frame[used++] = byte;
        if (used == 9) {
            const size_t len = frame[7] | ((size_t)frame[8] << 8);
            if (frame[2] != 2 || len > LINK_MAX_PAYLOAD) {
                used = total = 0;
                continue;
            }
            total = 11 + len;
        }
        if (total && used == total) {
            const size_t len = total - 11;
            const uint16_t crc = (uint16_t)frame[9 + len] | ((uint16_t)frame[10 + len] << 8);
            const uint16_t received_seq = (uint16_t)frame[5] | ((uint16_t)frame[6] << 8);
            if (frame[3] == 3 && received_seq == s_pending_sequence && crc == crc16(frame + 2, 7 + len)) {
                frame[9 + len] = '\0';
                const char *payload = (const char *)(frame + 9);
                const bool was_online = atomic_load(&s_online);
                if (was_online || strstr(payload, "\"device\":\"nodehexa\"") != NULL) {
                    if (!was_online) {
                        atomic_store(&s_bench, strstr(payload, "\"benchMode\":true") != NULL);
                        QM_LOGI(LOG_TAG, "NodeHexa online, bench=%d", atomic_load(&s_bench));
                    }
                    atomic_store(&s_online, true);
                    atomic_fetch_add(&s_rx_count, 1);
                    last_reply = xTaskGetTickCount();
                }
            }
            used = total = 0;
        }
    }
}

static void link_cli(char *out, int out_len, int argc, char **argv)
{
    (void)argc;
    (void)argv;
    snprintf(out, out_len, "ROBOT-LINK online=%d bench=%d tx=%u rx=%u\r\n",
             atomic_load(&s_online), atomic_load(&s_bench),
             atomic_load(&s_tx_count), atomic_load(&s_rx_count));
}

static const struct qm_cli_command s_cli = {
    .name = "robot",
    .help = "robot status: read-only NodeHexa UART link status",
    .function = link_cli,
};

int robot_link_init(void)
{
    uart_config_t config = {
        .baud_rate = 115200, .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, .source_clk = UART_SCLK_DEFAULT,
    };
    if (uart_is_driver_installed(LINK_UART) ||
        uart_param_config(LINK_UART, &config) != ESP_OK ||
        uart_set_pin(LINK_UART, LINK_TX, LINK_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE) != ESP_OK ||
        uart_driver_install(LINK_UART, 2048, 0, 0, NULL, 0) != ESP_OK) return -1;
    if (qm_cli_register_command(&s_cli) != 0) {
        uart_driver_delete(LINK_UART);
        return -1;
    }
    if (xTaskCreate(link_task, "robot_link", 4096, NULL, 5, NULL) != pdPASS) {
        qm_cli_unregister_command(&s_cli);
        uart_driver_delete(LINK_UART);
        return -1;
    }
    QM_LOGI(LOG_TAG, "UART2 TX=%d RX=%d ready; read-only probes", LINK_TX, LINK_RX);
    return 0;
}
