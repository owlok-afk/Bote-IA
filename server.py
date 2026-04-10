from fastmcp import FastMCP
import cv2
import base64
import requests
import serial
import time
import threading

# MCP APP

app = FastMCP(
    name="Bote IA",
    instructions="""
El sistema SOLO inicia cuando el usuario diga:
iniciar sistema

El sistema SOLO se detiene cuando el usuario diga:
detener sistema

Para vaciar el bote el usuario debe decir:
vaciar bote
"""
)

app.enable_tools = True
app.enable_auto_tool_choice = True
app.enable_tool_use = True

# CONFIG

LM_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "qwen/qwen3-vl-4b"

SERIAL_PORT = "COM3"
BAUDRATE = 9600
CAMERA_INDEX = 0

# ESTADO

sistema_activo = False
procesando_objeto = False
ultimo_procesamiento = 0
vaciando = False  # <-- NUEVO

frame_actual = None
lock_frame = threading.Lock()

angulo_servo_actual = 90

arduino = None
lock_serial = threading.Lock()

camara = None

# SERIAL

def iniciar_serial():
    global arduino

    try:
        arduino = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
        time.sleep(2)
        print("Arduino conectado")
    except:
        arduino = None
        print("Error puerto COM")

def mover_servo(angulo):
    global angulo_servo_actual

    if arduino is None:
        return

    with lock_serial:
        try:
            arduino.write(f"{angulo}\n".encode())
            angulo_servo_actual = angulo
            print("Servo ->", angulo)
        except:
            print("Error servo")

# CAMARA

def iniciar_camara():
    global camara

    if camara and camara.isOpened():
        return camara

    camara = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    camara.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("Camara iniciada")
    return camara

def loop_camara():
    global frame_actual

    cap = iniciar_camara()

    while True:

        if sistema_activo and not vaciando: 
            ret, frame = cap.read()

            if ret:
                with lock_frame:
                    frame_actual = frame.copy()

        time.sleep(0.03)

# MOVIMIENTO

detector = cv2.createBackgroundSubtractorMOG2(
    history=200,
    varThreshold=35,
    detectShadows=False
)

def detectar_movimiento(frame):
    mascara = detector.apply(frame)
    return cv2.countNonZero(mascara) > 1500

# RESET DETECTOR


def reiniciar_detector():
    global detector

    detector = cv2.createBackgroundSubtractorMOG2(
        history=200,
        varThreshold=35,
        detectShadows=False
    )

    print("Detector reiniciado")

# IA - PROMPT 


PROMPT = """Eres un clasificador de residuos. Analiza la imagen y responde SOLO con una palabra.

EJEMPLOS DE ORGANICO (responde: organico):
- cascara de platano, naranja, mango, limon
- fruta entera o mordida
- restos de comida, semillas, huesos

EJEMPLOS DE INORGANICO (responde: inorganico):
- botella de plastico (agua, refresco, jugo)
- botella de vidrio
- bolsa de plastico
- lata de metal
- carton o papel

Si no hay objeto visible o no estas seguro responde: sinbasura

Responde SOLO una palabra: organico, inorganico o sinbasura"""

def analizar_imagen(frame):

    frame = cv2.resize(frame, (224,224))

    _, buffer = cv2.imencode(".jpg", frame)
    img64 = base64.b64encode(buffer).decode()

    payload = {
        "model": MODEL_NAME,
        "temperature": 0,
        "max_tokens": 20,
        "messages":[
            {
                "role":"user",
                "content":[
                    {"type":"text","text":PROMPT},
                    {
                        "type":"image_url",
                        "image_url":{"url":f"data:image/jpeg;base64,{img64}"}
                    }
                ]
            }
        ]
    }

    try:
        r = requests.post(LM_URL, json=payload, timeout=60)
        respuesta = r.json()["choices"][0]["message"]["content"].lower().strip()

        print("IA raw:", respuesta)

        if "inorganico" in respuesta:
            return "inorganico"

        if "organico" in respuesta:
            return "organico"

        if "sinbasura" in respuesta or "sinbas" in respuesta or "sin basura" in respuesta:
            return "sinbasura"

        return "desconocido"

    except Exception as e:
        print("Error IA:", e)
        return "error"

# DOBLE VERIFICACION

def decision_final():

    with lock_frame:
        f1 = None if frame_actual is None else frame_actual.copy()

    if f1 is None:
        return "error"

    r1 = analizar_imagen(f1)

    time.sleep(0.6)

    with lock_frame:
        f2 = None if frame_actual is None else frame_actual.copy()

    if f2 is None:
        return "error"

    r2 = analizar_imagen(f2)

    print("Verificacion:", r1, r2)

    if r1 == r2:
        return r1

    return "desconocido"

# LOOP IA

def loop_ia():

    global procesando_objeto, ultimo_procesamiento

    while True:

        if not sistema_activo or vaciando:  # <-- PAUSAR SI VACIANDO
            time.sleep(0.2)
            continue

        if procesando_objeto:
            time.sleep(0.2)
            continue

        if time.time() - ultimo_procesamiento < 4:
            time.sleep(0.2)
            continue

        with lock_frame:
            frame = None if frame_actual is None else frame_actual.copy()

        if frame is None:
            time.sleep(0.2)
            continue

        if detectar_movimiento(frame):

            procesando_objeto = True
            ultimo_procesamiento = time.time()

            print("Objeto detectado")

            resultado = decision_final()

            print("Decision final:", resultado)

            if resultado == "organico":
                mover_servo(180)

            elif resultado == "inorganico":
                mover_servo(0)

            time.sleep(2)
            mover_servo(90)

            reiniciar_detector()

            procesando_objeto = False

        time.sleep(0.3)

# SECUENCIA DE VACIADO (hilo separado)

def secuencia_vaciado():
    global vaciando, procesando_objeto

    print("Iniciando vaciado...")

    # Esperar a que termine si hay un objeto siendo procesado
    while procesando_objeto:
        time.sleep(0.2)

    vaciando = True

    # Abrir compuerta: servo a 180
    print("Vaciando: servo -> 180")
    mover_servo(180)

    # Mantener abierto 10 segundos para sacar la basura
    time.sleep(10)

    # Cerrar compuerta: servo a 0
    print("Vaciando: servo -> 0")
    mover_servo(0)

    # Esperar otros 10 segundos en posicion cerrada
    time.sleep(10)

    # Regresar al centro y reanudar operacion normal
    mover_servo(90)
    reiniciar_detector()

    vaciando = False
    print("Vaciado completo, sistema reanudado")

# TOOLS MCP

@app.tool
def iniciar_sistema():
    global sistema_activo
    sistema_activo = True
    return "Sistema iniciado"

@app.tool
def detener_sistema():
    global sistema_activo
    sistema_activo = False
    return "Sistema detenido"

@app.tool
def angulo_actual():
    return f"Angulo actual {angulo_servo_actual}"

@app.tool
def vaciar():
    """Vacia el bote: pausa la camara, abre la compuerta 10s, cierra 10s y reanuda."""
    if vaciando:
        return "El bote ya se esta vaciando, espera a que termine"

    threading.Thread(target=secuencia_vaciado, daemon=True).start()
    return "Vaciado iniciado: servo a 180° por 10s, luego 0° por 10s, despues regresa a operacion normal"


# HILOS

def iniciar_hilos():

    iniciar_serial()

    threading.Thread(target=loop_camara, daemon=True).start()
    threading.Thread(target=loop_ia, daemon=True).start()

    print("Sistema listo")

iniciar_hilos()