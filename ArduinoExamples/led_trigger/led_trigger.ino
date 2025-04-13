/*
  Blink

  Turns an LED on for one second, then off for one second, repeatedly.

  Most Arduinos have an on-board LED you can control. On the UNO, MEGA and ZERO
  it is attached to digital pin 13, on MKR1000 on pin 6. LED_BUILTIN is set to
  the correct LED pin independent of which board is used.
  If you want to know what pin the on-board LED is connected to on your Arduino
  model, check the Technical Specs of your board at:
  https://www.arduino.cc/en/Main/Products
  https://www.arduino.cc/en/Tutorial/BuiltInExamples/Blink
*/

bool keepRunning = true;
char c;
// the setup function runs once when you press reset or power the board
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.begin(9600);
}

// the loop function runs over and over again forever
void loop() {
  // if we receive communication from user
  if (Serial.available() > 0) {
    // read what we receive
    c = Serial.read();
    // if it's our code, we activate heron 
    if (c == 'm') {
      digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
      delay(1000);
      digitalWrite(LED_BUILTIN, LOW);
    }
  }
}
