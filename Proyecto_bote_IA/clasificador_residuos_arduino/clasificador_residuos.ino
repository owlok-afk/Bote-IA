/*
  clasificador_residuos.ino
  Arduino Mega 2560 — Pin 8
  Sin sensor de distancia — la detección la hace Python por cámara.

  Comandos recibidos por Serial:
    PING       → "PONG"
    ORGANICO   → servo 180° → espera → 90° → "OK"
    INORGANICO → servo 0°   → espera → 90° → "OK"
    VACIAR     → servo 180° → espera → servo 0° → espera → 90° → "OK"
*/

#include <Servo.h>

// ─── CONFIGURACIÓN ───────────────────────────────────────────────
const int PIN_SERVO  = 8;
const int BAUDRATE   = 9600;

const int ANGULO_CENTRO     = 90;
const int ANGULO_ORGANICO   = 180;
const int ANGULO_INORGANICO = 0;
const int TIEMPO_ESPERA_MS  = 3000;  // Ajusta según tu tolva
const int TIEMPO_VACIADO_MS = 8000;  // Tiempo en cada extremo al vaciar

// ─── VARIABLES ───────────────────────────────────────────────────
Servo miServo;
String bufferSerial = "";

// ─── SETUP ───────────────────────────────────────────────────────
void setup() {
  Serial.begin(BAUDRATE);
  miServo.attach(PIN_SERVO);
  miServo.write(ANGULO_CENTRO);
  Serial.println("READY");
}

// ─── HELPERS ─────────────────────────────────────────────────────
void clasificar(int angulo) {
  miServo.write(angulo);
  delay(TIEMPO_ESPERA_MS);
  miServo.write(ANGULO_CENTRO);
  Serial.println("OK");
}

void vaciar() {
  miServo.write(ANGULO_ORGANICO);
  delay(TIEMPO_VACIADO_MS);
  miServo.write(ANGULO_INORGANICO);
  delay(TIEMPO_VACIADO_MS);
  miServo.write(ANGULO_CENTRO);
  Serial.println("OK");
}

void procesarComando(String cmd) {
  if      (cmd == "PING")       Serial.println("PONG");
  else if (cmd == "ORGANICO")   clasificar(ANGULO_ORGANICO);
  else if (cmd == "INORGANICO") clasificar(ANGULO_INORGANICO);
  else if (cmd == "VACIAR")     vaciar();
  else {
    Serial.print("ERROR:comando desconocido: ");
    Serial.println(cmd);
  }
}

// ─── LOOP ────────────────────────────────────────────────────────
void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      bufferSerial.trim();
      if (bufferSerial.length() > 0) procesarComando(bufferSerial);
      bufferSerial = "";
    } else {
      bufferSerial += c;
    }
  }
}
