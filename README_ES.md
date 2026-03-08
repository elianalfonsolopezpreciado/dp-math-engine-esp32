<div align="center">
  <img src="https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/esp32-paper1.jpeg" alt="ESP32-WROOM with Heat Sink" width="400">
  <p><i>Módulo ESP32-WROOM utilizado durante las pruebas, equipado con un disipador de calor para mitigar el estrés térmico durante ejecuciones prolongadas.</i></p>
</div>

[English Version](README.md)

# Dynamic Precision Math Engine para la Aceleración de Álgebra Lineal y Trigonometría en Microcontroladores Xtensa LX6

## Resumen

Este repositorio documenta el desarrollo y la evaluación empírica del **Dynamic Precision Math Engine**, un marco aritmético optimizado diseñado para tareas computacionales de alto rendimiento en microcontroladores basados en Xtensa LX6 (ESP32). Al transicionar de operaciones de punto flotante IEEE-754 a una arquitectura especializada de punto fijo Q16.16, e integrar un núcleo CORDIC de 16 iteraciones junto con algoritmos de multiplicación de matrices por teselas, el sistema logra reducciones sustanciales en la latencia de ejecución. Complementando al motor se encuentra el **ESP32 Academic Benchmark Lab**, una sofisticada suite de diagnóstico basada en Python que facilita el despliegue automatizado de firmware, la adquisición determinista de datos y una caracterización estadística rigurosa de las métricas de rendimiento.

---

## Arquitectura Técnica

### 1. Dynamic Precision Math Engine
Optimizado para la arquitectura de doble núcleo Xtensa LX6, el motor minimiza el consumo de ciclos de reloj para operaciones trascendentales y de álgebra lineal. Las características clave incluyen:
*   **Núcleo de Punto Fijo Q16.16:** Utiliza enteros con signo de 32 bits con precisión fraccional de 16 bits para aprovechar la tubería de enteros del procesador.
*   **Núcleo Trigonométrico CORDIC:** Una implementación de 16 iteraciones para Seno, Coseno y Arcotangente, utilizando normalización de cuadrantes para soporte de dominio completo.
*   **Motor de Álgebra Lineal por Teselas:** Multiplicación de matrices optimizada mediante el particionamiento en teselas para maximizar la utilización de registros y minimizar la sobrecarga de acceso a memoria.
*   **Conmutación Dinámica de Precisión:** Un mecanismo compatible con FreeRTOS que permite el ajuste en tiempo de ejecución entre rutas de ejecución optimizadas para rendimiento o precisión.

### 2. ESP32 Academic Benchmark Lab
Un entorno de control integrado desarrollado en Python que orquesta el ciclo de vida experimental. Gestiona la comunicación serial asíncrona con el dispositivo bajo prueba (DUT) y ejecuta protocolos automatizados de prueba A/B para asegurar la significancia estadística.

---

## Entorno de Desarrollo

*   **Entorno de Desarrollo Integrado (IDE):** Visual Studio Code
*   **Cadena de Herramientas:** Extensión ESP-IDF v5.4.3
*   **Plataforma de Hardware:** ESP32 (Xtensa LX6)

---

## Metodología Experimental

### Ejecución Automatizada del Benchmark
La siguiente demostración ilustra el flujo de trabajo experimental automatizado, incluyendo la orquestación del firmware y la adquisición de telemetría en tiempo real.

<div align="center">
  <video src="https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/1.mp4" muted autoplay loop controls width="800"></video>
</div>

### Inicialización y Monitoreo de Firmware
Análisis comparativo de la inicialización del sistema vía telemetría serial tanto para el Dynamic Engine propietario como para la implementación estándar IEEE-754.

| **Dynamic Precision Engine (Propietario)** | **Standard Math (IEEE-754)** |
|:---:|:---:|
| ![Inicialización del Sistema Propietario](https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/mo.png) | ![Inicialización del Sistema Estándar](https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/st.png) |
| *Salida del monitor serial durante la secuencia de arranque del Dynamic Engine.* | *Salida del monitor serial durante el arranque de la biblioteca matemática estándar.* |

---

## Caracterización de Rendimiento

El análisis del factor de aceleración del rendimiento demuestra la eficacia de las optimizaciones Q16.16 y CORDIC en diversos núcleos matemáticos.

<div align="center">
  <img src="https://github.com/elianalfonsolopezpreciado/resources/raw/main/paper/rendimiento_motor_matematico.png" alt="Comparativa de Aceleración de Rendimiento" width="800">
</div>

---

## Evolución y Versiones del Laboratorio

### v1.0 — Marco de Trabajo Base
Prototipo inicial con una GUI en CustomTkinter, flasheo automático mediante `esptool`, orquestación de protocolo A/B y exportación de datos (CSV, LaTeX).

### v1.1 — Robustez Serial Asíncrona
*   **Problema:** Interrupción del protocolo debido al acceso prematuro al puerto serial.
*   **Causa:** Condición de carrera durante el ciclo de arranque en caliente del ESP32 después del flasheo.
*   **Solución:** Se aumentó el tiempo de espera serial (1.0s), se implementaron retrasos de sincronización tras la reconexión y se aplicaron protocolos `reset_input_buffer()`.

### v1.2 — Arbitraje de Puertos a Nivel de SO
*   **Problema:** `PermissionError(13)` en las interfaces COM.
*   **Causa:** Bloqueo persistente de recursos por parte del sistema operativo Windows tras la terminación de `esptool`.
*   **Solución:** Cierre obligatorio del puerto serial antes de la reconexión e implementación de un bucle de adquisición iterativo.

### v1.3 — Compatibilidad de Esquema de Telemetría
*   **Problema:** Estructura inconsistente de los paquetes JSON.
*   **Causa:** Transición en la telemetría del firmware de la clave heredada `cycles` a `cycles_elapsed`.
*   **Solución:** Se implementó un mapeo dinámico de campos y una validación flexible de JSON.

### v1.4 — Desacoplamiento de Dimensionalidad de Datos
*   **Problema:** Fallo en el análisis debido a la falta de claves `input`.
*   **Causa:** Eliminación intencional de los escalares de entrada en la telemetría de alta frecuencia para reducir la sobrecarga de ancho de banda.
*   **Solución:** Verificación condicional de la existencia de columnas en la tubería estadística.

### v1.5 — Estandarización de Codificación de Caracteres
*   **Problema:** `UnicodeEncodeError` durante el renderizado de símbolos científicos.
*   **Causa:** Incompatibilidad entre Windows CP1252 y la notación matemática UTF-8 (ej. σ).
*   **Solución:** Aplicación universal de la codificación UTF-8 en todos los subsistemas de E/S.

### v1.6 — Abstracción de Dependencias
*   **Problema:** `Missing optional dependency 'Jinja2'` en las tuberías de LaTeX.
*   **Causa:** Dependencia de `to_latex` de Pandas con el motor Styler.
*   **Solución:** Utilización de `escape=False` para omitir los requisitos de Styler de alto nivel.

### v1.7 — Métricas Estadísticas Avanzadas
Integración de métricas de investigación robustas:
*   **Latencia Mediana:** Indicador resiliente de tendencia central.
*   **Desviación Absoluta Mediana (MAD):** Medida de dispersión resistente a valores atípicos.
*   **Jitter:** Definido como $\sigma / \mu$ para el análisis de varianza.
*   **Score de Determinismo:** $1 / (1 + Jitter)$ para la evaluación de la predictibilidad del sistema.

### v1.8 — Visualización Segura de Hilos
*   **Problema:** Condiciones de carrera en el motor de renderizado de la GUI de Matplotlib.
*   **Solución:** Se desacopló la visualización del hilo principal utilizando el backend no interactivo `Agg`.

---

## Referencia de Investigación
Para un análisis teórico completo y resultados revisados por pares:
[Dynamic_Precision_Math_Engine_on_Xtensa_LX6.pdf](paper/Dynamic_Precision_Math_Engine_for_Linear_Algebra_and_Trigonometry_Acceleration_on_Xtensa_LX6_Microcontrollers.pdf)

---
© 2026 Elian Alfonso Lopez Preciado.
