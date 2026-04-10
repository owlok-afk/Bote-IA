#include <Servo.h>

Servo servo;

void setup() {
  Serial.begin(9600);
  servo.attach(8);
  servo.write(90);
  Serial.println("Arduino listo");
}

void loop() {
  if (Serial.available() > 0) {
    String dato = Serial.readStringUntil('\n');
    dato.trim();
    int angulo = dato.toInt();

    if (angulo >= 0 && angulo <= 180) {
      servo.write(angulo);
      Serial.print("Servo movido a: ");
      Serial.println(angulo);
    }
  }
}