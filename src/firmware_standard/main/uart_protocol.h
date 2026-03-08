/*
 * Purpose: UART JSON line protocol shared by the benchmark host interface.
 * Algorithm used: UART0 line-oriented receive loop with cJSON parsing and
 * unformatted JSON transmission after each benchmark measurement.
 * Known limitations: commands longer than the fixed receive buffer are truncated
 * and rejected; only the run_suite command is handled.
 * Paper section: Experimental control and data capture protocol for benchmark runs.
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "cJSON.h"
#include "driver/uart.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"

namespace UartProtocol {

static constexpr uart_port_t UART_PORT = UART_NUM_0;
static constexpr int UART_BAUD = 115200;
static constexpr int UART_RX_BUF = 2048;
static constexpr int UART_TX_BUF = 4096;

struct RunCommand {
    bool valid;
    uint16_t tests;
    uint32_t seed;
};

inline void init() {
    const uart_config_t uart_config = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .rx_flow_ctrl_thresh = 0,
        .source_clk = UART_SCLK_APB,
    };
    uart_driver_install(UART_PORT, UART_RX_BUF, UART_TX_BUF, 0, nullptr, 0);
    uart_param_config(UART_PORT, &uart_config);
    uart_set_pin(UART_PORT, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
}

inline void send_line(const char* line) {
    uart_write_bytes(UART_PORT, line, strlen(line));
    uart_write_bytes(UART_PORT, "\n", 1);
}

inline void send_json(cJSON* json) {
    char* rendered = cJSON_PrintUnformatted(json);
    if (rendered != nullptr) {
        send_line(rendered);
        cJSON_free(rendered);
    }
}

inline void send_ready(const char* firmware_name) {
    cJSON* root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "event", "ready");
    cJSON_AddStringToObject(root, "firmware", firmware_name);
    cJSON_AddNumberToObject(root, "cpu_mhz", 240);
    cJSON_AddStringToObject(root, "idf_version", esp_get_idf_version());
    send_json(root);
    cJSON_Delete(root);
}

inline void send_suite_complete(uint16_t total_tests) {
    cJSON* root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "event", "suite_complete");
    cJSON_AddNumberToObject(root, "total_tests", total_tests);
    send_json(root);
    cJSON_Delete(root);
}

inline bool read_line(char* buffer, size_t capacity, TickType_t timeout_ticks) {
    if (capacity == 0) {
        return false;
    }

    size_t index = 0;
    while (index + 1 < capacity) {
        uint8_t ch = 0;
        const int read = uart_read_bytes(UART_PORT, &ch, 1, timeout_ticks);
        if (read <= 0) {
            return false;
        }
        if (ch == '\r') {
            continue;
        }
        if (ch == '\n') {
            buffer[index] = '\0';
            return index > 0;
        }
        buffer[index++] = static_cast<char>(ch);
    }

    buffer[capacity - 1] = '\0';
    return false;
}

inline RunCommand parse_run_command(const char* line) {
    RunCommand cmd = {false, 300, 0};
    cJSON* root = cJSON_Parse(line);
    if (root == nullptr) {
        return cmd;
    }

    const cJSON* cmd_item = cJSON_GetObjectItemCaseSensitive(root, "cmd");
    const cJSON* tests_item = cJSON_GetObjectItemCaseSensitive(root, "tests");
    const cJSON* seed_item = cJSON_GetObjectItemCaseSensitive(root, "seed");

    if (cJSON_IsString(cmd_item) &&
        strcmp(cmd_item->valuestring, "run_suite") == 0 &&
        cJSON_IsNumber(seed_item)) {
        cmd.valid = true;
        cmd.seed = static_cast<uint32_t>(seed_item->valuedouble);
        if (cJSON_IsNumber(tests_item) && tests_item->valuedouble > 0) {
            const double requested = tests_item->valuedouble;
            cmd.tests = static_cast<uint16_t>(requested > 300.0 ? 300 : requested);
        }
    }

    cJSON_Delete(root);
    return cmd;
}

}  // namespace UartProtocol
