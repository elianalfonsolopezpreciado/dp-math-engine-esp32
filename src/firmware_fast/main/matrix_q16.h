/*
 * Purpose: Q16.16 matrix multiplication kernel for 4x4, 8x8, and 16x16 benchmark cases.
 * Algorithm used: heap-backed dense matrices with loop tiling and 64-bit
 * accumulators; fixed-point scaling is deferred until each output element completes.
 * Known limitations: TILE_SIZE is larger than benchmark matrices, so tiling mainly
 * preserves the intended algorithm structure rather than changing access patterns.
 * Paper section: Linear algebra acceleration benchmark for the fixed-point engine.
 */

#pragma once

#include <stdint.h>
#include <string.h>

#include "fast_math_engine.h"

namespace FastMathEngine {

static constexpr int TILE_SIZE = 32;

struct Matrix {
    int32_t* data;
    uint16_t rows;
    uint16_t cols;
};

inline void matmul_q16(const Matrix& A, const Matrix& B, Matrix& C) {
    memset(C.data, 0, sizeof(int32_t) * C.rows * C.cols);

    for (uint16_t ii = 0; ii < A.rows; ii += TILE_SIZE) {
        const uint16_t i_end = static_cast<uint16_t>((ii + TILE_SIZE) < A.rows ? (ii + TILE_SIZE) : A.rows);
        for (uint16_t jj = 0; jj < B.cols; jj += TILE_SIZE) {
            const uint16_t j_end = static_cast<uint16_t>((jj + TILE_SIZE) < B.cols ? (jj + TILE_SIZE) : B.cols);
            for (uint16_t i = ii; i < i_end; ++i) {
                for (uint16_t j = jj; j < j_end; ++j) {
                    int64_t acc = 0;
                    for (uint16_t kk = 0; kk < A.cols; kk += TILE_SIZE) {
                        const uint16_t k_end = static_cast<uint16_t>((kk + TILE_SIZE) < A.cols ? (kk + TILE_SIZE) : A.cols);
                        for (uint16_t k = kk; k < k_end; ++k) {
                            acc += static_cast<int64_t>(A.data[i * A.cols + k]) *
                                   static_cast<int64_t>(B.data[k * B.cols + j]);
                        }
                    }
                    C.data[i * C.cols + j] = static_cast<int32_t>(acc >> Q_FRACT_BITS);
                }
            }
        }
    }
}

}  // namespace FastMathEngine
