// Include the Arduino Stepper Library
#include <Stepper.h>

//speed of predator
int speedHeron=20;
//revolutions of stepper motor - adapt how far your predator should go in void heron-
const int stepsPerRevolution=200;
char c;

// Create Instance of Stepper library
Stepper myStepper(stepsPerRevolution, 8, 9, 10, 11);

// flag to control serial reading
bool keepRunning = true;

// the setup function runs once when you press reset or power the board
void setup() {
  // set speed of heron
  myStepper.setSpeed(speedHeron);
  //initialize serial port
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
        heron();
      }
    }
}

void heron(){
   // step one revolution in one direction:
  myStepper.step(stepsPerRevolution/2); //change here how many rotations should you do
  delay(3000);
  
  // step one revolution in the other direction:
  myStepper.step(-stepsPerRevolution/2); // change here too to come back to normal position
  delay(10000);
  myStepper.setSpeed(0);
}
