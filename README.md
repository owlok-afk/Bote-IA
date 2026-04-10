<div align="center">

# Clasificador Inteligente de Basura con IA

**Sistema automático de separación de residuos orgánicos e inorgánicos usando inteligencia artificial, Arduino y un modelo de IA local**


</div>

---

## Descripción del Proyecto

Este proyecto implementa un **varios elementos basicos** modificados para que sean capaces de **detectar, analizar y clasificar residuos automáticamente** e:

- Orgánicos  
- Inorgánicos  

El sistema utiliza una **cámara web**, un **modelo de visión artificial ejecutado localmente** y un **servomotor controlado por Arduino** para mover físicamente una compuerta dentro del bote.

El flujo es completamente automático:
1. Se detecta movimiento (objeto presente)
2. Se captura imagen
3. La IA analiza el tipo de residuo
4. Se mueve el servo según el resultado

---

## Características Principales

- Clasificación automática de residuos
- IA local (sin internet)
- Detección por movimiento (sin sensores físicos)
- Validación doble para mayor precisión
- Comunicación Arduino ↔ Python por Serial
- Control mediante servidor MCP (FastMCP)

---

## Hardware Utilizado

| Componente | Función |
|:--|:--|
| Arduino UNO | Control del servomotor |
| Servomotor | Movimiento de compuerta del bote |
| Webcam USB | Captura de imágenes |
| Bote de basura | Estructura física del sistema |

---

## Conexiones

| Pin Arduino | Componente |
|:--|:--|
| `8` | Señal del servo |
| `5V` | Alimentación |
| `GND` | Tierra |

---

---

## Flujo del Sistema

```mermaid
flowchart TD
    A["Sistema activo"] --> B["Captura de frame"]
    B --> C{"¿Movimiento detectado?"}
    C -- No --> B
    C -- Sí --> D["Tomar imagen"]
    D --> E["Analizar con IA"]
    E --> F{"Resultado"}
    F -- Orgánico --> G["Servo → 180°"]
    F -- Inorgánico --> H["Servo → 0°"]
    F -- Desconocido --> I["No acción"]
    G --> J["Regresar servo a 90°"]
    H --> J
    I --> B
    J --> B

