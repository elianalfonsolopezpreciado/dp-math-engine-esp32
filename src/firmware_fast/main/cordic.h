/*
 * Purpose: Integer-only CORDIC trigonometric engine for benchmarked sin/cos paths.
 * Algorithm used: 16-iteration rotation-mode CORDIC in Q16.16 with quadrant
 * normalization to map the full [-pi, pi] domain into the principal interval.
 * Known limitations: output precision is bounded by 16 iterations and Q16.16
 * quantization; angles outside the wrapped domain are normalized by subtraction.
 * Paper section: Trigonometric acceleration benchmark for the Xtensa LX6 fast
 * math engine using fixed-point CORDIC.
 */

#pragma once

#include <stdint.h>

#include "fast_math_engine.h"

namespace FastMathEngine {

static constexpr q16_t PI_Q = 205887;
static constexpr q16_t HALF_PI_Q = 102944;
static constexpr q16_t TWO_PI_Q = 411775;
static constexpr q16_t K_INV = 39797;

static constexpr q16_t atan_table[16] = {
    51472, 30386, 16055, 8150, 4091, 2047, 1024, 512,
    256, 128, 64, 32, 16, 8, 4, 2
};

inline q16_t normalize_angle(q16_t theta) {
    while (theta > PI_Q) {
        theta = static_cast<q16_t>(theta - TWO_PI_Q);
    }
    while (theta < -PI_Q) {
        theta = static_cast<q16_t>(theta + TWO_PI_Q);
    }
    return theta;
}

inline void cordic_sin_cos(q16_t theta, q16_t* sin_out, q16_t* cos_out) {
    theta = normalize_angle(theta);

    int32_t cos_sign = 1;
    if (theta > HALF_PI_Q) {
        theta = static_cast<q16_t>(PI_Q - theta);
        cos_sign = -1;
    } else if (theta < -HALF_PI_Q) {
        theta = static_cast<q16_t>(-PI_Q - theta);
        cos_sign = -1;
    }

    q16_t x = K_INV;
    q16_t y = 0;
    q16_t z = theta;

    for (int i = 0; i < 16; ++i) {
        const q16_t x_shift = static_cast<q16_t>(x >> i);
        const q16_t y_shift = static_cast<q16_t>(y >> i);
        if (z >= 0) {
            x = static_cast<q16_t>(x - y_shift);
            y = static_cast<q16_t>(y + x_shift);
            z = static_cast<q16_t>(z - atan_table[i]);
        } else {
            x = static_cast<q16_t>(x + y_shift);
            y = static_cast<q16_t>(y - x_shift);
            z = static_cast<q16_t>(z + atan_table[i]);
        }
    }

    *sin_out = y;
    *cos_out = static_cast<q16_t>(cos_sign > 0 ? x : -x);
}

}  // namespace FastMathEngine
