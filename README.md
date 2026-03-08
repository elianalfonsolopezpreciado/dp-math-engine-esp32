# Dynamic Precision Math Engine for Linear Algebra and Trigonometry Acceleration on Xtensa LX6 Microcontrollers

## Abstract / Resumen

**English:**
This repository documents the development and empirical evaluation of the **Dynamic Precision Math Engine**, an optimized arithmetic framework engineered for high-throughput computational tasks on Xtensa LX6-based microcontrollers (ESP32). By pivoting from standard IEEE-754 floating-point operations to a specialized Q16.16 fixed-point architecture, and integrating a 16-iteration CORDIC (Coordinate Rotation Digital Computer) kernel alongside tiled matrix multiplication algorithms, the system achieves substantial reductions in execution latency. Complementing the engine is the **ESP32 Academic Benchmark Lab**, a sophisticated Python-based diagnostic suite that facilitates automated firmware deployment, deterministic data acquisition, and rigorous statistical characterization of performance metrics.

**Español:**
Este repositorio documenta el desarrollo y la evaluación empírica del **Dynamic Precision Math Engine**, un marco aritmético optimizado diseñado para tareas computacionales de alto rendimiento en microcontroladores basados en Xtensa LX6 (ESP32). Al transicionar de operaciones de punto flotante IEEE-754 a una arquitectura especializada de punto fijo Q16.16, e integrar un núcleo CORDIC de 16 iteraciones junto con algoritmos de multiplicación de matrices por teselas, el sistema logra reducciones sustanciales en la latencia de ejecución. Complementando al motor se encuentra el **ESP32 Academic Benchmark Lab**, una sofisticada suite de diagnóstico basada en Python que facilita el despliegue automatizado de firmware, la adquisición determinista de datos y una caracterización estadística rigurosa de las métricas de rendimiento.

---

## Technical Architecture / Arquitectura Técnica

### 1. Dynamic Precision Math Engine
**English:** Optimized for the dual-core Xtensa LX6 architecture, the engine minimizes clock cycle consumption for transcendental and linear algebra operations. Key features include:
*   **Q16.16 Fixed-Point Core:** Utilizes 32-bit signed integers with 16-bit fractional precision to leverage the processor's integer pipeline.
*   **CORDIC Trigonometric Kernel:** A 16-iteration implementation for Sine, Cosine, and Arctangent, utilizing quadrant normalization for full-circle domain support.
*   **Tiled Linear Algebra Engine:** Matrix multiplication optimized via loop tiling to maximize register utilization and minimize memory access overhead.
*   **Dynamic Precision Switching:** A FreeRTOS-compatible mechanism allowing for runtime adjustment between performance-optimized and precision-optimized execution paths.

**Español:** Optimizado para la arquitectura de doble núcleo Xtensa LX6, el motor minimiza el consumo de ciclos de reloj para operaciones trascendentales y de álgebra lineal. Las características clave incluyen:
*   **Núcleo de Punto Fijo Q16.16:** Utiliza enteros con signo de 32 bits con precisión fraccional de 16 bits para aprovechar la tubería de enteros del procesador.
*   **Núcleo Trigonométrico CORDIC:** Una implementación de 16 iteraciones para Seno, Coseno y Arcotangente, utilizando normalización de cuadrantes para soporte de dominio completo.
*   **Motor de Álgebra Lineal por Teselas:** Multiplicación de matrices optimizada mediante el particionamiento en teselas para maximizar la utilización de registros y minimizar la sobrecarga de acceso a memoria.
*   **Conmutación Dinámica de Precisión:** Un mecanismo compatible con FreeRTOS que permite el ajuste en tiempo de ejecución entre rutas de ejecución optimizadas para rendimiento o precisión.

### 2. ESP32 Academic Benchmark Lab
**English:** An integrated control environment developed in Python that orchestrates the experimental lifecycle. It manages asynchronous serial communication with the DUT (Device Under Test) and performs automated A/B testing protocols to ensure statistical significance.
**Español:** Un entorno de control integrado desarrollado en Python que orquesta el ciclo de vida experimental. Gestiona la comunicación serial asíncrona con el dispositivo bajo prueba (DUT) y ejecuta protocolos automatizados de prueba A/B para asegurar la significancia estadística.

---

## Development Environment / Entorno de Desarrollo

**English:**
*   **Integrated Development Environment (IDE):** Visual Studio Code
*   **Toolchain:** ESP-IDF v5.4.3 Extension
*   **Hardware Platform:** ESP32 (Xtensa LX6)

**Español:**
*   **Entorno de Desarrollo Integrado (IDE):** Visual Studio Code
*   **Cadena de Herramientas:** Extensión ESP-IDF v5.4.3
*   **Plataforma de Hardware:** ESP32 (Xtensa LX6)

---

## Experimental Methodology / Metodología Experimental

### Automated Benchmark Execution / Ejecución Automatizada del Benchmark
**English:** The following demonstration illustrates the automated experimental workflow, including firmware orchestration and real-time telemetry acquisition.
**Español:** La siguiente demostración ilustra el flujo de trabajo experimental automatizado, incluyendo la orquestación del firmware y la adquisición de telemetría en tiempo real.

<div align="center">
  <video src="https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/1.mp4" muted autoplay loop controls width="800"></video>
</div>

### Firmware Initialization and Monitoring / Inicialización y Monitoreo de Firmware
**English:** Comparative analysis of system initialization via serial telemetry for both the proprietary Dynamic Engine and the standard IEEE-754 implementation.
**Español:** Análisis comparativo de la inicialización del sistema vía telemetría serial tanto para el Dynamic Engine propietario como para la implementación estándar IEEE-754.

| **Dynamic Precision Engine (Proprietary)** | **Standard Math (IEEE-754)** |
|:---:|:---:|
| ![Proprietary System Initialization](https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/mo.png) | ![Standard System Initialization](https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/st.png) |
| *Serial monitor output during Dynamic Engine boot sequence.* | *Serial monitor output during standard math library boot.* |

---

## Performance Characterization / Caracterización de Rendimiento

**English:** The performance speedup analysis demonstrates the efficacy of the Q16.16 and CORDIC optimizations across various mathematical kernels.
**Español:** El análisis del factor de aceleración del rendimiento demuestra la eficacia de las optimizaciones Q16.16 y CORDIC en diversos núcleos matemáticos.

<div align="center">
  <img src="https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/rendimiento_motor_matematico.png" alt="Performance Acceleration Comparison" width="800">
</div>

---

## Evolution and Versioning / Evolución y Versiones del Laboratorio

### v1.0 — Baseline Framework / Marco de Trabajo Base
Initial prototype featuring a CustomTkinter GUI, automated flashing via `esptool`, A/B protocol orchestration, and data exporting (CSV, LaTeX).

### v1.1 — Asynchronous Serial Robustness / Robustez Serial Asíncrona
*   **Problem:** Protocol disruption due to premature serial port access.
*   **Cause:** Race condition during ESP32 warm-boot cycle post-flash.
*   **Solution:** Increased serial timeout (1.0s), implemented post-reconnect synchronization delays, and enforced `reset_input_buffer()` protocols.

### v1.2 — OS-Level Port Arbitration / Arbitraje de Puertos a Nivel de SO
*   **Problem:** `PermissionError(13)` on COM interfaces.
*   **Cause:** Persistent resource locking by the Windows operating system after `esptool` termination.
*   **Solution:** Mandatory serial closure prior to reconnection and implementation of an iterative acquisition loop.

### v1.3 — Telemetry Schema Compatibility / Compatibilidad de Esquema de Telemetría
*   **Problem:** Inconsistent JSON packet structure.
*   **Cause:** Transition in firmware telemetry from legacy `cycles` to `cycles_elapsed`.
*   **Solution:** Implemented dynamic field mapping and flexible JSON validation.

### v1.4 — Data Dimensionality Decoupling / Desacoplamiento de Datos
*   **Problem:** Analysis failure due to missing `input` keys.
*   **Cause:** Intentional removal of input scalars from high-frequency telemetry to reduce bandwidth overhead.
*   **Solution:** Conditional verification of column existence in the statistical pipeline.

### v1.5 — Character Encoding Standardization / Estandarización de Codificación
*   **Problem:** `UnicodeEncodeError` during scientific symbol rendering.
*   **Cause:** Incompatibility between Windows CP1252 and UTF-8 mathematical notation (e.g., σ).
*   **Solution:** Universal enforcement of UTF-8 encoding across all I/O subsystems.

### v1.6 — Dependency Abstraction / Abstracción de Dependencias
*   **Problem:** `Missing optional dependency 'Jinja2'` in LaTeX pipelines.
*   **Cause:** Pandas `to_latex` dependency on the Styler engine.
*   **Solution:** Utilization of `escape=False` to bypass high-level Styler requirements.

### v1.7 — Advanced Statistical Metrics / Métricas Estadísticas Avanzadas
Integration of robust research metrics:
*   **Median Latency:** Resilient central tendency indicator.
*   **Median Absolute Deviation (MAD):** Outlier-resistant dispersion measure.
*   **Jitter:** Defined as $\sigma / \mu$ for variance analysis.
*   **Determinism Score:** $1 / (1 + Jitter)$ for system predictability assessment.

### v1.8 — Thread-Safe Visualization / Visualización Segura de Hilos
*   **Problem:** Race conditions in the Matplotlib GUI rendering engine.
*   **Solution:** Decoupled visualization from the main thread using the non-interactive `Agg` backend.

---

## Research Reference / Referencia de Investigación
**English:** For comprehensive theoretical analysis and peer-reviewed results:
**Español:** Para un análisis teórico completo y resultados revisados por pares:
[Dynamic_Precision_Math_Engine_on_Xtensa_LX6.pdf](paper/Dynamic_Precision_Math_Engine_for_Linear_Algebra_and_Trigonometry_Acceleration_on_Xtensa_LX6_Microcontrollers.pdf)

---
© 2026 Elian Alfonso Lopez Preciado.
