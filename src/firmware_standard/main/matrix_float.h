/*
 * Purpose: Baseline dense matrix multiplication kernel for the IEEE754 benchmark firmware.
 * Algorithm used: naive triple-loop matrix multiplication with float accumulation
 * and no tiling, blocking, or cache-aware optimization.
 * Known limitations: intended as an unoptimized reference path; numerical error
 * follows standard float accumulation order and execution is not throughput-tuned.
 * Paper section: Baseline linear algebra benchmark against the optimized fixed-point path.
 */

#pragma once

#include <stdint.h>
#include <string.h>

struct MatrixF {
    float* data;
    uint16_t rows;
    uint16_t cols;
};

inline void matmul_float(const MatrixF& A, const MatrixF& B, MatrixF& C) {
    memset(C.data, 0, sizeof(float) * C.rows * C.cols);
    for (uint16_t i = 0; i < A.rows; ++i) {
        for (uint16_t j = 0; j < B.cols; ++j) {
            float acc = 0.0f;
            for (uint16_t k = 0; k < A.cols; ++k) {
                acc += A.data[i * A.cols + k] * B.data[k * B.cols + j];
            }
            C.data[i * C.cols + j] = acc;
        }
    }
}
