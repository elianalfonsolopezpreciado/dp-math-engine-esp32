/*
 * Purpose: Q16.16 fixed-point arithmetic core for scalar and matrix benchmarks.
 * Algorithm used: signed 32-bit fixed-point math with 16 fractional bits and
 * 64-bit intermediates for multiplication.
 * Known limitations: representable range is approximately [-32768, 32767.9999];
 * conversions from float round to nearest and may saturate at the int32_t bounds.
 * Paper section: Fixed-point arithmetic engine used by the dynamic precision math
 * engine benchmark in the linear algebra and scalar multiplication sections.
 */

#pragma once

#include <stdint.h>
#include <limits.h>
#include <math.h>

namespace FastMathEngine {

typedef int32_t q16_t;
static constexpr int Q_FRACT_BITS = 16;
static constexpr q16_t Q_ONE = (1 << Q_FRACT_BITS);

inline q16_t floatToQ(float val) {
    const float scaled = val * static_cast<float>(Q_ONE);
    if (scaled >= static_cast<float>(INT32_MAX)) {
        return INT32_MAX;
    }
    if (scaled <= static_cast<float>(INT32_MIN)) {
        return INT32_MIN;
    }
    return static_cast<q16_t>(lrintf(scaled));
}

inline float qToFloat(q16_t val) {
    return static_cast<float>(val) / static_cast<float>(Q_ONE);
}

inline q16_t mulQ(q16_t a, q16_t b) {
    return static_cast<q16_t>((static_cast<int64_t>(a) * static_cast<int64_t>(b)) >> Q_FRACT_BITS);
}

inline q16_t mulQ_sat(q16_t a, q16_t b) {
    const int64_t prod = (static_cast<int64_t>(a) * static_cast<int64_t>(b)) >> Q_FRACT_BITS;
    if (prod > INT32_MAX) {
        return INT32_MAX;
    }
    if (prod < INT32_MIN) {
        return INT32_MIN;
    }
    return static_cast<q16_t>(prod);
}

inline q16_t addQ(q16_t a, q16_t b) {
    return static_cast<q16_t>(a + b);
}

inline q16_t subQ(q16_t a, q16_t b) {
    return static_cast<q16_t>(a - b);
}

}  // namespace FastMathEngine
