#include "IrSensor.h"
#include "WifiTimeUtils.h"

// Initialize global variables
unsigned long touchStartMs = 0;
unsigned long pauseStartMs = 0;


int pauseDurationMs = 30; 
double currentTouchX = 0;
double currentTouchY = 0;
unsigned long currentMs = 0; 

int touchDurationMs = 120; 

double detectedTouchX = 0;
double detectedTouchY = 0;

bool touchDetected = false; 
bool timeoutOccurred = false; 
bool detectionStarted = false;
unsigned long timeoutDurationMs = 180000; 




bool touchFlag = false;

TouchState touchState;

void init_sensor() {
    Serial.println("Sensor init: Starting");
    zforce.Start(DATA_READY);
    Message *msg = nullptr;

    Serial.println("Sensor init: ReverseX");
    zforce.ReverseX(false);

    do {
        msg = zforce.GetMessage();
    } while (msg == nullptr);

    if (msg->type == MessageType::REVERSEXTYPE) {
        Serial.println("Received ReverseX Response");
        Serial.print("Message type is: ");
        Serial.println((int)msg->type);
    }
    zforce.DestroyMessage(msg); // Free memory here

    Serial.println("Sensor init: ReverseY");
    zforce.ReverseY(false);

    do {
        msg = zforce.GetMessage();
    } while (msg == nullptr);

    if (msg->type == MessageType::REVERSEYTYPE) {
        Serial.println("Received ReverseY Response");
        Serial.print("Message type is: ");
        Serial.println((int)msg->type);
    }
    zforce.DestroyMessage(msg); // Free memory here

    Serial.println("Sensor init: TouchActiveArea");
    zforce.TouchActiveArea(0, 0, 4000, 4000);

    do {
        msg = zforce.GetMessage();
    } while (msg == nullptr);

    if (msg->type == MessageType::TOUCHACTIVEAREATYPE) {
        Serial.print("minX is: ");
        Serial.println(((TouchActiveAreaMessage *)msg)->minX);
        Serial.print("minY is: ");
        Serial.println(((TouchActiveAreaMessage *)msg)->minY);
        Serial.print("maxX is: ");
        Serial.println(((TouchActiveAreaMessage *)msg)->maxX);
        Serial.print("maxY is: ");
        Serial.println(((TouchActiveAreaMessage *)msg)->maxY);
    }
    zforce.DestroyMessage(msg); // Free memory here

    zforce.Enable(true);

    do {
        msg = zforce.GetMessage();
    } while (msg == nullptr);

    if (msg->type == MessageType::ENABLETYPE) {
        Serial.print("Message type is: ");
        Serial.println((int)msg->type);
        Serial.println("Sensor is now enabled and will report touches.");
    }
    zforce.DestroyMessage(msg); // Free memory here

    do {
        msg = zforce.GetMessage();
    } while (msg == nullptr);

    if (msg->type == MessageType::BOOTCOMPLETETYPE) {
        Serial.print("Message type is: ");
        Serial.println((int)msg->type);
        Serial.println("Boot complete message received.");
    }
    zforce.DestroyMessage(msg); // Free memory here
}




void sensor_get_value() {
    unsigned long functionStartMs = millis();
    timeoutOccurred = false;

    while(1) {
        currentMs = millis();
        if (currentMs - functionStartMs > timeoutDurationMs) {
            timeoutOccurred = true;
            
            detectedTouchX = 0;
            detectedTouchY = 0;
            break;
        }

        bool touched = queryTouch();
        if (touchState == NO_TOUCH) {
            if (touched) {
                touchState = TOUCH_START;
            }
        } else if (touchState == TOUCH_START) {
            touchStartMs = currentMs;
            touchState = TOUCH_PROGRESS;
        } else if (touchState == TOUCH_PROGRESS) {
            if ((currentMs - touchStartMs) > touchDurationMs) {
                touchState = TOUCH_DETECTED;
            } else if (!touched) {
                touchState = PAUSE_START;
            }
        } else if (touchState == PAUSE_START) {
            pauseStartMs = currentMs;
            touchState = PAUSE_PROGRESS;
        } else if (touchState == PAUSE_PROGRESS) {
            if ((currentMs - pauseStartMs) > pauseDurationMs) {
                touchState = NO_TOUCH;
                detectedTouchX = 0;
                detectedTouchY = 0;
                break;
            } else if (touched) {
                touchState = TOUCH_PROGRESS;
            }
        } else if (touchState == TOUCH_DETECTED) {
            detectedTouchX = currentTouchX;
            detectedTouchY = currentTouchY;
            touchState = NO_TOUCH;
            break;
        }
    }
}

bool queryTouch() {
    Message* touch = zforce.GetMessage();

    if (touch != nullptr) {
        if (touch->type == MessageType::TOUCHTYPE) {
            uint8_t touchCount = ((TouchMessage*)touch)->touchCount;
            currentTouchX = 0;
            currentTouchY = 0;
            for (uint8_t i = 0; i < touchCount; i++) {
                currentTouchX += ((TouchMessage*)touch)->touchData[i].x;
                currentTouchY += ((TouchMessage*)touch)->touchData[i].y;
            }
            currentTouchX /= touchCount;
            currentTouchY /= touchCount;
            zforce.DestroyMessage(touch); // Free memory here
            return true;
        } else if (touch->type == MessageType::BOOTCOMPLETETYPE) {
            Serial.println("Boot Complete Message received. Reinitializing touch sensor...");
            init_sensor(); 
            zforce.DestroyMessage(touch); // Free memory here
            return false;
        }
        zforce.DestroyMessage(touch); // Free memory here for any other type
    }
    return false;
}

//https://github.com/neonode-inc/zforce-arduino/blob/master/example/zForceLibraryExampleCode/zForceLibraryExampleCode.ino
