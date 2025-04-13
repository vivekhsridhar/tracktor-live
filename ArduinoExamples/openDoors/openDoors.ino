// Include the Arduino accelStepper.h library:
#include <AccelStepper.h>

// Define number of steps per rotation:

#define FULLSTEP 4

const int stepsTurn = 2038;
const int buttonPin = 6 ;
char c;

// Wiring:
// Pin 8 to IN1 on the ULN2003 driver
// Pin 9 to IN2 on the ULN2003 driver
// Pin 10 to IN3 on the ULN2003 driver
// Pin 11 to IN4 on the ULN2003 driver

// Create stepper object called 'stepper1' and 'stepper2', one for each door, note the pin order:
AccelStepper stepper1 (FULLSTEP, 8, 10, 9, 11);
AccelStepper stepper2 (FULLSTEP, 2, 4, 3, 5);


// flag to control serial reading
bool keepRunning = true;

// the setup function runs once when you press reset or power the board
void setup() {
  stepper1.setMaxSpeed(1000.0);
  stepper1.setAcceleration(50.0);
  stepper1.setSpeed(200);

  // set the same for motor 2
  stepper2.setMaxSpeed(1000.0);
  stepper2.setAcceleration(50.0);
  stepper2.setSpeed(200);
  
  // Begin Serial communication at a baud rate of 9600:
  Serial.begin(9600);
}

//We begin the loop during the experiment
void loop() {
   // if we receive communication from user
    if (Serial.available() > 0) {
      // read what we receive
      c = Serial.read();
      // if it's our code, we activate doors, wait 5s, and activate them in the opposite direction.
      if (c == 'm') {
        openOneCloseTwo();
        delay(5000);
        closeOneOpenTwo();
      }
    }
}

//define functions:

//This code opens door one, turning as far as stepsTurn, while closes door two.
//Note that door two should be open at the start of experiment, at the desired distance (stepsTurn).
void openOneCloseTwo(){
   stepper1.moveTo(stepsTurn);
   stepper1.run();
   stepper2.moveTo(-stepsTurn);
   stepper2.run();
}

//This code closes door one and opens door two (returning door two to the original position).
void closeOneOpenTwo(){
   stepper1.moveTo(0);
   stepper1.run();
   stepper2.moveTo(0);
   stepper2.run();
}
