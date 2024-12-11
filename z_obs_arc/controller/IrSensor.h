//IRSENSOR_H
#ifndef IrSensor_H
#define IrSensor_H

#include <Arduino.h>
#include "Zforce.h"


#define DATA_READY D7 // the pin of ESP connected to B0 of IR sensor


// Function declarations
void init_sensor();
void sensor_get_value();
bool queryTouch();


// Global variables related to IR sensor
extern unsigned long touchStartMs;
extern unsigned long pauseStartMs;
extern unsigned long currentMs;
extern int touchDurationMs;
extern int pauseDurationMs;  
extern double currentTouchX;
extern double currentTouchY;



extern double detectedTouchX;
extern double detectedTouchY;
extern bool touchFlag;
extern bool touchDetected;
extern bool timeoutOccurred;


enum TouchState {
    NO_TOUCH,
    TOUCH_START,
    TOUCH_PROGRESS,
    PAUSE_START,
    PAUSE_PROGRESS,
    TOUCH_DETECTED
};


#endif 
