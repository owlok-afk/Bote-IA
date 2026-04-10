
#include <Servo.h>

// ----- CONFIGURACION -----
const int PIN_SERVO = 9;   // Pin PWM donde va el servo
const int BAUDRATE  = 9600; // Debe coincidir con Python (BAUDRATE = 9600)

// ----- VARIABLES -----
Servo miServo;
String bufferSerial = "";  // Acumula caracteres hasta recibir '\n'

// ----- SETUP -----
void setup() {
  Serial.begin(BAUDRATE);

  miServo.attach(PIN_SERVO);
  miServo.write(90);  // Posicion inicial: centro

  Serial.println("Arduino listo");
}

// ----- LOOP -----
void loop() {

  // Leer caracteres del puerto Serial uno por uno
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\n') {
      // Llegó un salto de linea: procesar el dato recibido
      bufferSerial.trim();  // Quitar espacios o '\r' extra

      if (bufferSerial.length() > 0) {
        int angulo = bufferSerial.toInt();  // Convertir texto a numero

        // Validar que el angulo este en rango
        if (angulo >= 0 && angulo <= 180) {
          miServo.write(angulo);
          Serial.print("Servo movido a: ");
          Serial.println(angulo);
        } else {
          Serial.println("Error: angulo fuera de rango (0-180)");
        }
      }

      bufferSerial = "";  // Limpiar buffer para el siguiente dato

    } else {
      bufferSerial += c;  // Seguir acumulando caracteres
    }
  }
}
