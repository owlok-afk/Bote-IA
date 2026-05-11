#!/usr/bin/env python3
"""
service.py — Loop autónomo de clasificación de residuos.
Detección por movimiento de cámara (BackgroundSubtractorMOG2).
Ctrl+C para detener.
# Presiona 'v' + Enter para vaciar. (funcionalidad de vaciado desactivada temporalmente)

Uso:
    python service.py
    python service.py --port COM5 --camera 1
"""

import argparse
import signal
import sys
import time
import threading
import select
from datetime import datetime

import cv2

import arduino
import camara
import clasificador

# === DETECCIÓN DE MOVIMIENTO ===
MOTION_PIXEL_THRESHOLD = 1500
COOLDOWN_SECONDS = 5.0

_detector = cv2.createBackgroundSubtractorMOG2(
    history=200, varThreshold=35, detectShadows=False
)

def _reset_detector():
    global _detector
    _detector = cv2.createBackgroundSubtractorMOG2(
        history=200, varThreshold=35, detectShadows=False
    )

def _hay_movimiento(frame) -> bool:
    mascara = _detector.apply(frame)
    return cv2.countNonZero(mascara) > MOTION_PIXEL_THRESHOLD

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# === ESTADO ===
_running  = False
# _vaciando = False  # (vaciado desactivado temporalmente)
_vaciando = False     # mantenido como False fijo para no romper referencias
_stats    = {"cycles": 0, "organico": 0, "inorganico": 0, "discarded": 0}


# === VACIADO (desactivado temporalmente) ===

# def _secuencia_vaciado():
#     global _vaciando
#     if _vaciando:
#         log("WARN  vaciado ya en curso")
#         return
#     _vaciando = True
#     log("INFO  iniciando vaciado...")
#     result = arduino.vaciar()
#     if result["success"]:
#         log("INFO  vaciado completado")
#     else:
#         log(f"ERROR vaciado fallido: {result.get('error', result.get('response'))}")
#     _reset_detector()
#     _vaciando = False


# def _escuchar_teclado():
#     """Hilo que escucha 'v' sin bloquear Ctrl+C."""
#     while _running:
#         # select permite esperar entrada con timeout, sin bloquear el proceso
#         try:
#             listo, _, _ = select.select([sys.stdin], [], [], 0.5)
#             if listo:
#                 tecla = sys.stdin.readline().strip().lower()
#                 if tecla == "v":
#                     threading.Thread(target=_secuencia_vaciado, daemon=True).start()
#         except Exception:
#             break


# === LOOP PRINCIPAL ===

def sorting_loop():
    global _running

    ultimo_proceso = 0.0

    while _running:
        if _vaciando:
            time.sleep(0.2)
            continue

        frame = camara.capture_frame()
        if frame is None:
            log("WARN  camara no disponible")
            time.sleep(0.5)
            continue

        if time.time() - ultimo_proceso < COOLDOWN_SECONDS:
            time.sleep(0.1)
            continue

        if not _hay_movimiento(frame):
            time.sleep(0.1)
            continue

        _stats["cycles"] += 1
        ultimo_proceso = time.time()

        time.sleep(0.3)

        img_b64 = camara.get_camera_data()
        if not img_b64:
            log("ERROR captura de imagen fallida")
            continue

        status = clasificador.act_on_waste(img_b64)

        parts  = status.split(":")
        action = parts[0]

        if action == "SUCCESS":
            obj      = parts[1] if len(parts) > 1 else "?"
            category = parts[2] if len(parts) > 2 else "?"
            log(f"OK    {obj} -> {category}")
            if category == "ORGANICO":
                _stats["organico"] += 1
            else:
                _stats["inorganico"] += 1

        elif action == "DISCARD":
            log("WARN  sin objeto reconocido, descartado")
            _stats["discarded"] += 1

        else:
            log(f"ERROR clasificacion fallida: {':'.join(parts[1:])}")
            _stats["discarded"] += 1

        _reset_detector()


# === ARRANQUE ===

def signal_handler(sig, frame):
    global _running
    _running = False
    print()
    log(f"Sistema detenido  |  organico={_stats['organico']}  inorganico={_stats['inorganico']}  descartados={_stats['discarded']}")
    camara.close()
    arduino.close()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",   type=str, help="Puerto serial (e.g. COM3)")
    parser.add_argument("--camera", type=int, default=0, help="Indice de camara")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    _running = True

    if args.port:
        arduino.SERIAL_PORT = args.port
    camara.CAMERA_INDEX = args.camera

    if not clasificador.test_connection():
        log("ERROR no se pudo conectar a LM Studio")
        sys.exit(1)

    log("INFO  sistema listo, esperando objetos...  (Ctrl+C para detener)")
    # log("INFO  sistema listo, esperando objetos...  (v + Enter para vaciar | Ctrl+C para detener)")

    # threading.Thread(target=_escuchar_teclado, daemon=True).start()  # (vaciado desactivado temporalmente)

    try:
        sorting_loop()
    except Exception as e:
        log(f"ERROR excepcion no controlada: {e}")
    finally:
        camara.close()
        arduino.close()
