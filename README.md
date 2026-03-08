# Dynamic Precision Math Engine for Linear Algebra and Trigonometry Acceleration on Xtensa LX6 Microcontrollers

<div align="center">
  <img src="https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/esp32-paper1.jpeg" alt="ESP32-WROOM with Heat Sink" width="300">
  <p><i>ESP32-WROOM module utilized during testing, equipped with a custom heat sink to mitigate thermal stress during prolonged benchmark execution.</i></p>
</div>

[Versión en Español](README_ES.md)

## Abstract

This repository documents the development and empirical evaluation of the **Dynamic Precision Math Engine**, an optimized arithmetic framework engineered for high-throughput computational tasks on Xtensa LX6-based microcontrollers (ESP32). By pivoting from standard IEEE-754 floating-point operations to a specialized Q16.16 fixed-point architecture, and integrating a 16-iteration CORDIC (Coordinate Rotation Digital Computer) kernel alongside tiled matrix multiplication algorithms, the system achieves substantial reductions in execution latency. Complementing the engine is the **ESP32 Academic Benchmark Lab**, a sophisticated Python-based diagnostic suite that facilitates automated firmware deployment, deterministic data acquisition, and rigorous statistical characterization of performance metrics.

### Publication Status
*   **Status:** Preprint (Under Review)
*   **Target Repository:** [arxiv.org](https://arxiv.org)
*   **License:** arXiv.org Perpetual Non-exclusive License
*   **Categories:** Computer Science (cs.PF - Performance)

---

## Technical Architecture

### 1. Dynamic Precision Math Engine
Optimized for the dual-core Xtensa LX6 architecture, the engine minimizes clock cycle consumption for transcendental and linear algebra operations. Key features include:
*   **Q16.16 Fixed-Point Core:** Utilizes 32-bit signed integers with 16-bit fractional precision to leverage the processor's integer pipeline.
*   **CORDIC Trigonometric Kernel:** A 16-iteration implementation for Sine, Cosine, and Arctangent, utilizing quadrant normalization for full-circle domain support.
*   **Tiled Linear Algebra Engine:** Matrix multiplication optimized via loop tiling to maximize register utilization and minimize memory access overhead.
*   **Dynamic Precision Switching:** A FreeRTOS-compatible mechanism allowing for runtime adjustment between performance-optimized and precision-optimized execution paths.

### 2. ESP32 Academic Benchmark Lab
An integrated control environment developed in Python that orchestrates the experimental lifecycle. It manages asynchronous serial communication with the DUT (Device Under Test) and performs automated A/B testing protocols to ensure statistical significance.

---

## Source Code Breakdown

### Proprietary Optimized Firmware (`src/firmware_fast`)
This directory contains the custom-engineered fixed-point math engine. It is designed to maximize throughput by avoiding the overhead of the ESP32's floating-point unit (FPU) where possible.
*   **`fast_math_engine.h`**: Implements the Q16.16 arithmetic core using 32-bit signed integers and 64-bit intermediates for overflow-safe multiplication.
*   **`cordic.h`**: A zero-floating-point CORDIC implementation for trigonometric functions (sin/cos), utilizing quadrant normalization to handle the full [-π, π] range.
*   **`matrix_q16.h`**: High-performance matrix multiplication kernel utilizing loop tiling (32x32 tiles) to optimize cache behavior and register usage.
*   **`benchmark_suite.h`**: Orchestrates the experimental protocol, utilizing the Xtensa `ccount` register for nanosecond-level cycle measurements and a deterministic LCG (Linear Congruential Generator) for reproducible test data.

### Standard Reference Firmware (`src/firmware_standard`)
This directory provides the baseline implementation using standard IEEE-754 single-precision floating-point arithmetic for performance comparison.
*   **`standard_math.h`**: Thin wrappers around the standard C `math.h` library (`sinf`, `cosf`) and native floating-point operators.
*   **`matrix_float.h`**: A naive triple-loop matrix multiplication implementation without tiling or optimization, serving as the architectural baseline.
*   **`benchmark_suite.h`**: Parallel to the fast version, it executes the same test vectors but targets the standard floating-point execution path to quantify the speedup ratio.

---

## Development Environment

*   **Integrated Development Environment (IDE):** Visual Studio Code
*   **Toolchain:** ESP-IDF v5.4.3 Extension
*   **Hardware Platform:** ESP32 (Xtensa LX6)

---

## Experimental Methodology

### Automated Benchmark Execution
The following demonstration illustrates the automated experimental workflow, including firmware orchestration and real-time telemetry acquisition.

<div align="center">
  <a href="https://drive.google.com/file/d/1T0rxlihR3cxLFi2EU41E5WtueGxBTuF3/view?usp=sharing" target="_blank">
    <img src="https://raw.githubusercontent.com/elianalfonsolopezpreciado/resources/main/paper/rendimiento_motor_matematico.png" alt="Watch the Execution Video" width="400">
    <br>
    <b>[Click here to watch the laboratory execution video on Google Drive]</b>
  </a>
  <p><i>Note: The video demonstrates the automated flashing and benchmark protocol.</i></p>
</div>

### Firmware Initialization and Monitoring
Comparative analysis of system initialization via serial telemetry for both the proprietary Dynamic Engine and the standard IEEE-754 implementation.

| **Dynamic Precision Engine (Proprietary)** | **Standard Math (IEEE-754)** |
|:---:|:---:|
| ![Proprietary System Initialization](https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/mo.png) | ![Standard System Initialization](https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/st.png) |
| *Serial monitor output during Dynamic Engine boot sequence.* | *Serial monitor output during standard math library boot.* |

---

## Performance Characterization

The performance speedup analysis demonstrates the efficacy of the Q16.16 and CORDIC optimizations compared to the standard IEEE-754 floating-point baseline.

<div align="center">
  <img src="https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/fig3_speedup_ratio.png" alt="Performance Acceleration Comparison (English)" width="800">
</div>

---

## Evolution and Versioning

### v1.0 — Baseline Framework
Initial prototype featuring a CustomTkinter GUI, automated flashing via `esptool`, A/B protocol orchestration, and data exporting (CSV, LaTeX).

### v1.1 — Asynchronous Serial Robustness
*   **Problem:** Protocol disruption due to premature serial port access.
*   **Cause:** Race condition during ESP32 warm-boot cycle post-flash.
*   **Solution:** Increased serial timeout (1.0s), implemented post-reconnect synchronization delays, and enforced `reset_input_buffer()` protocols.

### v1.2 — OS-Level Port Arbitration
*   **Problem:** `PermissionError(13)` on COM interfaces.
*   **Cause:** Persistent resource locking by the Windows operating system after `esptool` termination.
*   **Solution:** Mandatory serial closure prior to reconnection and implementation of an iterative acquisition loop.

### v1.3 — Telemetry Schema Compatibility
*   **Problem:** Inconsistent JSON packet structure.
*   **Cause:** Transition in firmware telemetry from legacy `cycles` to `cycles_elapsed`.
*   **Solution:** Implemented dynamic field mapping and flexible JSON validation.

### v1.4 — Data Dimensionality Decoupling
*   **Problem:** Analysis failure due to missing `input` keys.
*   **Cause:** Intentional removal of input scalars from high-frequency telemetry to reduce bandwidth overhead.
*   **Solution:** Conditional verification of column existence in the statistical pipeline.

### v1.5 — Character Encoding Standardization
*   **Problem:** `UnicodeEncodeError` during scientific symbol rendering.
*   **Cause:** Incompatibility between Windows CP1252 and UTF-8 mathematical notation (e.g., σ).
*   **Solution:** Universal enforcement of UTF-8 encoding across all I/O subsystems.

### v1.6 — Dependency Abstraction
*   **Problem:** `Missing optional dependency 'Jinja2'` in LaTeX pipelines.
*   **Cause:** Pandas `to_latex` dependency on the Styler engine.
*   **Solution:** Utilization of `escape=False` to bypass high-level Styler requirements.

### v1.7 — Advanced Statistical Metrics
Integration of robust research metrics:
*   **Median Latency:** Resilient central tendency indicator.
*   **Median Absolute Deviation (MAD):** Outlier-resistant dispersion measure.
*   **Jitter:** Defined as $\sigma / \mu$ for variance analysis.
*   **Determinism Score:** $1 / (1 + Jitter)$ for system predictability assessment.

### v1.8 — Thread-Safe Visualization
*   **Problem:** Race conditions in the Matplotlib GUI rendering engine.
*   **Solution:** Decoupled visualization from the main thread using the non-interactive `Agg` backend.

---

## Research Reference
For comprehensive theoretical analysis and peer-reviewed results:
[Dynamic_Precision_Math_Engine_on_Xtensa_LX6.pdf](paper/Dynamic_Precision_Math_Engine_for_Linear_Algebra_and_Trigonometry_Acceleration_on_Xtensa_LX6_Microcontrollers.pdf)

---
© 2026 Elian Alfonso Lopez Preciado.
