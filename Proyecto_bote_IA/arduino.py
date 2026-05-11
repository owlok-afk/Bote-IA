"""
arduino.py — Persistent serial connection to the Waste Sorter Arduino.

Sin sensor de distancia. La detección de objetos la hace Python
mediante análisis de movimiento por cámara (BackgroundSubtractorMOG2).

Comandos soportados:
  PING       → PONG
  ORGANICO   → OK   (servo gira a bin orgánico, espera y vuelve al centro)
  INORGANICO → OK   (servo gira a bin inorgánico, espera y vuelve al centro)
"""

import time
import threading
import glob
import serial

# === CONFIGURACIÓN ===
SERIAL_PORT = "COM3"    # Ej: "COM3" en Windows, "/dev/ttyUSB0" en Linux
SERIAL_BAUD = 9600

TIMEOUT_SHORT = 5       # PING
TIMEOUT_SORT  = 10      # ORGANICO / INORGANICO (servo + margen)

# === ESTADO INTERNO ===
_serial_lock = threading.Lock()
_serial_conn: serial.Serial | None = None


# ─── Conexión ────────────────────────────────────────────────────

def _auto_detect_port() -> str | None:
    for pattern in ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/cu.usbserial*"]:
        ports = glob.glob(pattern)
        if ports:
            return ports[0]
    for n in range(1, 21):
        port = f"COM{n}"
        try:
            s = serial.Serial(port, SERIAL_BAUD, timeout=0.5)
            s.close()
            return port
        except serial.SerialException:
            pass
    return None


def _get_serial() -> serial.Serial:
    global _serial_conn
    if _serial_conn is not None and _serial_conn.is_open:
        return _serial_conn

    port = SERIAL_PORT or _auto_detect_port()
    if port is None:
        raise serial.SerialException(
            "No se encontró Arduino. Configura arduino.SERIAL_PORT manualmente."
        )

    _serial_conn = serial.Serial(port, SERIAL_BAUD, timeout=TIMEOUT_SHORT)
    time.sleep(2)  # Esperar reset del Arduino

    # Drenar el mensaje "READY" inicial
    while _serial_conn.in_waiting:
        _serial_conn.readline()

    return _serial_conn


# ─── API pública ─────────────────────────────────────────────────

def send_command(command: str, timeout: float = TIMEOUT_SHORT) -> dict:
    """Envía un comando al Arduino y devuelve la respuesta (thread-safe)."""
    global _serial_conn
    with _serial_lock:
        try:
            ser = _get_serial()
            ser.timeout = timeout
            ser.reset_input_buffer()
            ser.write(f"{command}\n".encode())
            response = ser.readline().decode().strip()
            return {
                "success":  response in ("OK", "PONG"),
                "response": response,
            }
        except serial.SerialException as e:
            try:
                if _serial_conn:
                    _serial_conn.close()
            except Exception:
                pass
            _serial_conn = None
            return {"success": False, "error": f"Serial error: {e}"}


def ping() -> dict:
    """Prueba la conexión con el Arduino."""
    return send_command("PING")


def classify_as_organico() -> dict:
    """Activa el servo para depositar en el bin ORGÁNICO."""
    return send_command("ORGANICO", timeout=TIMEOUT_SORT)


def classify_as_inorganico() -> dict:
    """Activa el servo para depositar en el bin INORGÁNICO."""
    return send_command("INORGANICO", timeout=TIMEOUT_SORT)


def close():
    """Cierra la conexión serial limpiamente."""
    global _serial_conn
    with _serial_lock:
        if _serial_conn and _serial_conn.is_open:
            _serial_conn.close()
        _serial_conn = None


# === VACIADO (desactivado temporalmente) ===
# def vaciar() -> dict:
#     """Vacía ambos compartimentos moviendo el servo a cada extremo."""
#     return send_command("VACIAR", timeout=30)
