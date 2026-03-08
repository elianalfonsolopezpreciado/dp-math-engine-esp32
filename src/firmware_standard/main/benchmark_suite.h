/*
 * Purpose: Benchmark harness for the IEEE754 firmware with deterministic test
 * generation, cycle counting, and JSON result emission.
 * Algorithm used: seeded linear congruential generator (multiplier 1664525,
 * increment 1013904223, modulus 2^32), single-shot measurements with interrupts
 * disabled, and Core 1 task pinning for every suite run.
 * Known limitations: the suite is serialized on one task and allocates matrices
 * from the heap per test; matrix accuracy is summarized by Frobenius norm only.
 * Paper section: Benchmark methodology and experimental protocol execution.
 */

#pragma once

#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

#include "cJSON.h"
#include "esp_heap_caps.h"
#include "esp_rom_crc.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "xtensa/core-macros.h"

#include "matrix_float.h"
#include "standard_math.h"
#include "uart_protocol.h"

namespace BenchmarkSuite {

static constexpr const char* FIRMWARE_NAME = "StandardMath_IEEE754";
static constexpr float PI_F = 3.14159265358979323846f;
static constexpr uint16_t TOTAL_TESTS = 300;

struct SuiteArgs {
    uint32_t seed;
    uint16_t count;
};

static volatile bool g_suite_running = false;

inline float lcg_next_float(uint32_t* state, float min, float max) {
    *state = (*state * 1664525u) + 1013904223u;
    const float normalized = static_cast<float>(*state) / 4294967295.0f;
    return min + ((max - min) * normalized);
}

inline uint32_t matrix_input_crc32(const float* a, const float* b, size_t count) {
    uint32_t crc = esp_rom_crc32_le(0, reinterpret_cast<const uint8_t*>(a), count * sizeof(float));
    crc = esp_rom_crc32_le(crc, reinterpret_cast<const uint8_t*>(b), count * sizeof(float));
    return crc;
}

inline double matrix_norm_double(const double* data, size_t count) {
    double sum = 0.0;
    for (size_t i = 0; i < count; ++i) {
        sum += data[i] * data[i];
    }
    return sqrt(sum);
}

inline float matrix_norm_float(const float* data, size_t count) {
    double sum = 0.0;
    for (size_t i = 0; i < count; ++i) {
        const double value = static_cast<double>(data[i]);
        sum += value * value;
    }
    return static_cast<float>(sqrt(sum));
}

inline void add_optional_number(cJSON* root, const char* key, bool present, double value) {
    if (present) {
        cJSON_AddNumberToObject(root, key, value);
    } else {
        cJSON_AddNullToObject(root, key);
    }
}

inline void emit_result(
    int test_id,
    const char* category,
    const char* function_name,
    bool has_input_scalar,
    double input_scalar,
    bool has_matrix_hash,
    uint32_t matrix_hash,
    bool has_result_scalar,
    double result_scalar,
    bool has_result_matrix_norm,
    double result_matrix_norm,
    bool has_reference_scalar,
    double reference_scalar,
    bool has_reference_matrix_norm,
    double reference_matrix_norm,
    double abs_error,
    uint32_t cycles_start,
    uint32_t cycles_end) {

    cJSON* root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "firmware", FIRMWARE_NAME);
    cJSON_AddNumberToObject(root, "test_id", test_id);
    cJSON_AddStringToObject(root, "category", category);
    cJSON_AddStringToObject(root, "function", function_name);
    add_optional_number(root, "input_scalar", has_input_scalar, input_scalar);
    if (has_matrix_hash) {
        cJSON_AddNumberToObject(root, "input_matrix_hash", matrix_hash);
    } else {
        cJSON_AddNullToObject(root, "input_matrix_hash");
    }
    add_optional_number(root, "result_scalar", has_result_scalar, result_scalar);
    add_optional_number(root, "result_matrix_norm", has_result_matrix_norm, result_matrix_norm);
    add_optional_number(root, "reference_scalar", has_reference_scalar, reference_scalar);
    add_optional_number(root, "reference_matrix_norm", has_reference_matrix_norm, reference_matrix_norm);
    cJSON_AddNumberToObject(root, "abs_error", abs_error);
    cJSON_AddNumberToObject(root, "cycles_start", cycles_start);
    cJSON_AddNumberToObject(root, "cycles_end", cycles_end);
    cJSON_AddNumberToObject(root, "cycles_elapsed", static_cast<uint32_t>(cycles_end - cycles_start));
    cJSON_AddNumberToObject(root, "ram_free_bytes", esp_get_free_heap_size());
    cJSON_AddNumberToObject(root, "core", xPortGetCoreID());
    cJSON_AddNumberToObject(root, "cpu_freq_mhz", 240);
    cJSON_AddNumberToObject(root, "timestamp_ms", esp_timer_get_time() / 1000);
    UartProtocol::send_json(root);
    cJSON_Delete(root);
}

inline void run_scalar_trig_test(int test_id, const char* category, const char* function_name, float angle) {
    portDISABLE_INTERRUPTS();
    const uint32_t cycles_start = xthal_get_ccount();
    const float result = (function_name[0] == 's') ? std_sin(angle) : std_cos(angle);
    const uint32_t cycles_end = xthal_get_ccount();
    portENABLE_INTERRUPTS();

    const double reference = (function_name[0] == 's')
        ? sin(static_cast<double>(angle))
        : cos(static_cast<double>(angle));
    emit_result(
        test_id,
        category,
        function_name,
        true,
        angle,
        false,
        0,
        true,
        result,
        false,
        0.0,
        true,
        reference,
        false,
        0.0,
        fabs(static_cast<double>(result) - reference),
        cycles_start,
        cycles_end);
}

inline void run_scalar_mul_test(int test_id, float a, float b) {
    portDISABLE_INTERRUPTS();
    const uint32_t cycles_start = xthal_get_ccount();
    const float result = std_mul(a, b);
    const uint32_t cycles_end = xthal_get_ccount();
    portENABLE_INTERRUPTS();

    const double reference = static_cast<double>(a) * static_cast<double>(b);
    emit_result(
        test_id,
        "scalar_mul",
        "mul",
        true,
        a,
        false,
        0,
        true,
        result,
        false,
        0.0,
        true,
        reference,
        false,
        0.0,
        fabs(static_cast<double>(result) - reference),
        cycles_start,
        cycles_end);
}

inline void run_matrix_test(int test_id, uint16_t dim, const char* category, uint32_t* rng_state) {
    const size_t count = static_cast<size_t>(dim) * static_cast<size_t>(dim);
    float* raw_a = static_cast<float*>(heap_caps_malloc(sizeof(float) * count, MALLOC_CAP_8BIT));
    float* raw_b = static_cast<float*>(heap_caps_malloc(sizeof(float) * count, MALLOC_CAP_8BIT));
    float* raw_c = static_cast<float*>(heap_caps_malloc(sizeof(float) * count, MALLOC_CAP_8BIT));
    double* ref_c = static_cast<double*>(heap_caps_malloc(sizeof(double) * count, MALLOC_CAP_8BIT));

    if (raw_a == nullptr || raw_b == nullptr || raw_c == nullptr || ref_c == nullptr) {
        free(raw_a);
        free(raw_b);
        free(raw_c);
        free(ref_c);
        return;
    }

    for (size_t i = 0; i < count; ++i) {
        raw_a[i] = lcg_next_float(rng_state, -1.0f, 1.0f);
        raw_b[i] = lcg_next_float(rng_state, -1.0f, 1.0f);
    }

    MatrixF A = {raw_a, dim, dim};
    MatrixF B = {raw_b, dim, dim};
    MatrixF C = {raw_c, dim, dim};

    portDISABLE_INTERRUPTS();
    const uint32_t cycles_start = xthal_get_ccount();
    matmul_float(A, B, C);
    const uint32_t cycles_end = xthal_get_ccount();
    portENABLE_INTERRUPTS();

    for (uint16_t i = 0; i < dim; ++i) {
        for (uint16_t j = 0; j < dim; ++j) {
            double acc = 0.0;
            for (uint16_t k = 0; k < dim; ++k) {
                acc += static_cast<double>(raw_a[i * dim + k]) * static_cast<double>(raw_b[k * dim + j]);
            }
            ref_c[i * dim + j] = acc;
        }
    }

    const float result_norm = matrix_norm_float(raw_c, count);
    const double reference_norm = matrix_norm_double(ref_c, count);
    emit_result(
        test_id,
        category,
        "matmul",
        false,
        0.0,
        true,
        matrix_input_crc32(raw_a, raw_b, count),
        false,
        0.0,
        true,
        result_norm,
        false,
        0.0,
        true,
        reference_norm,
        fabs(static_cast<double>(result_norm) - reference_norm),
        cycles_start,
        cycles_end);

    free(raw_a);
    free(raw_b);
    free(raw_c);
    free(ref_c);
}

inline void run_overhead_test(int test_id) {
    volatile int dispatch = test_id & 3;

    portDISABLE_INTERRUPTS();
    const uint32_t cycles_start = xthal_get_ccount();
    switch (dispatch) {
        case 0:
            dispatch += 1;
            break;
        case 1:
            dispatch += 2;
            break;
        case 2:
            dispatch += 3;
            break;
        default:
            dispatch += 4;
            break;
    }
    const uint32_t cycles_end = xthal_get_ccount();
    portENABLE_INTERRUPTS();

    emit_result(
        test_id,
        "overhead",
        "switch",
        false,
        0.0,
        false,
        0,
        false,
        0.0,
        false,
        0.0,
        false,
        0.0,
        false,
        0.0,
        0.0,
        cycles_start,
        cycles_end);
}

inline void suite_task(void* arg) {
    SuiteArgs args = *static_cast<SuiteArgs*>(arg);
    free(arg);

    uint32_t rng_state = args.seed;
    const uint16_t count = args.count > TOTAL_TESTS ? TOTAL_TESTS : args.count;
    int test_id = 0;

    for (; test_id < 50 && test_id < count; ++test_id) {
        run_scalar_trig_test(test_id, "trig_sin", "sin", lcg_next_float(&rng_state, -PI_F, PI_F));
    }
    for (; test_id < 100 && test_id < count; ++test_id) {
        run_scalar_trig_test(test_id, "trig_cos", "cos", lcg_next_float(&rng_state, -PI_F, PI_F));
    }

    static constexpr float canonical_angles[20] = {
        0.0f, PI_F / 6.0f, -PI_F / 6.0f, PI_F / 4.0f, -PI_F / 4.0f,
        PI_F / 3.0f, -PI_F / 3.0f, PI_F / 2.0f, -PI_F / 2.0f, PI_F,
        -PI_F, 3.0f * PI_F / 2.0f, -3.0f * PI_F / 2.0f, 2.0f * PI_F, -2.0f * PI_F,
        PI_F / 6.0f, -PI_F / 6.0f, PI_F / 2.0f, -PI_F / 2.0f, 0.0f
    };
    for (int i = 0; test_id < 120 && test_id < count; ++i, ++test_id) {
        const bool sin_case = ((test_id - 100) % 2) == 0;
        run_scalar_trig_test(test_id, sin_case ? "trig_sin" : "trig_cos", sin_case ? "sin" : "cos", canonical_angles[i]);
    }

    for (; test_id < 160 && test_id < count; ++test_id) {
        run_matrix_test(test_id, 4, "matmul_4x4", &rng_state);
    }
    for (; test_id < 190 && test_id < count; ++test_id) {
        run_matrix_test(test_id, 8, "matmul_8x8", &rng_state);
    }
    for (; test_id < 210 && test_id < count; ++test_id) {
        run_matrix_test(test_id, 16, "matmul_16x16", &rng_state);
    }
    for (; test_id < 260 && test_id < count; ++test_id) {
        const float a = lcg_next_float(&rng_state, -100.0f, 100.0f);
        const float b = lcg_next_float(&rng_state, -100.0f, 100.0f);
        run_scalar_mul_test(test_id, a, b);
    }
    for (; test_id < 280 && test_id < count; ++test_id) {
        const bool near_positive = ((test_id - 260) % 2) == 0;
        const float center = near_positive ? (PI_F / 2.0f) : (-PI_F / 2.0f);
        const float angle = lcg_next_float(&rng_state, center - 0.01f, center + 0.01f);
        const bool sin_case = ((test_id - 260) % 4) < 2;
        run_scalar_trig_test(test_id, "boundary", sin_case ? "sin" : "cos", angle);
    }
    for (; test_id < 300 && test_id < count; ++test_id) {
        run_overhead_test(test_id);
    }

    UartProtocol::send_suite_complete(count);
    g_suite_running = false;
    vTaskDelete(nullptr);
}

inline void run_benchmark_suite(uint32_t seed, uint16_t count) {
    if (g_suite_running) {
        return;
    }

    SuiteArgs* args = static_cast<SuiteArgs*>(malloc(sizeof(SuiteArgs)));
    if (args == nullptr) {
        return;
    }

    args->seed = seed;
    args->count = (count == 0) ? TOTAL_TESTS : count;
    g_suite_running = true;
    xTaskCreatePinnedToCore(suite_task, "benchmark_suite", 8192, args, 5, nullptr, 1);
}

}  // namespace BenchmarkSuite
