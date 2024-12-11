#include "BeamBreak.h"
#include <Arduino.h>  

int sensorState = 0, lastState = 0;
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 200;
int reading = 0; 

void setupBeamBreak() {
    pinMode(SENSORPIN, INPUT_PULLUP);  
}


void activateBeamBreak() {

        reading = digitalRead(SENSORPIN);

       
        if (reading != lastState) {
            // Reset the debouncing timer
            lastDebounceTime = millis();
        }

        if ((millis() - lastDebounceTime) > debounceDelay) {
            // If the state has changed, update the sensor state
            if (reading != sensorState) {
                sensorState = reading;


            }
        }

        lastState = reading;
        delay(10);
    
}

void deactivateBeamBreak() {
    sensorState = -1;
    lastState = -1;
    lastDebounceTime = 0;
    reading = -1; 

    Serial.println("Beam break sensor deactivated");
}
