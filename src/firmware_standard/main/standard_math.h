/*
 * Purpose: Thin IEEE754 single-precision wrappers for the baseline benchmark firmware.
 * Algorithm used: direct delegation to sinf, cosf, and native float multiplication
 * with no lookup tables, memoization, or approximation shortcuts.
 * Known limitations: behavior follows libm single-precision accuracy and the ESP32
 * floating-point execution path; no explicit error-control features are added.
 * Paper section: Baseline floating-point math implementation for comparison against
 * the custom fixed-point engine.
 */

#pragma once

#include <math.h>

inline float std_sin(float x) {
    return sinf(x);
}

inline float std_cos(float x) {
    return cosf(x);
}

inline float std_mul(float a, float b) {
    return a * b;
}
