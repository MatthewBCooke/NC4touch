//Reward.cpp
#include "Reward.h"

bool isPriming = false;
unsigned long rewardDurationMs = 1000; 

void setupReward() {
    //pinMode(M2, OUTPUT);
    //digitalWrite(M2, LOW); 

    // PWM configuration
    ledcAttachPin(E2, PUMP_PWM_CHANNEL);
    ledcSetup(PUMP_PWM_CHANNEL, FREQ, RESOLUTION);
}

void dispenseReward() {
    ledcWrite(PUMP_PWM_CHANNEL, 255);
}

void stopRewardDispense() {
    ledcWrite(PUMP_PWM_CHANNEL, 0);
}

void primeFeedingTube() {
    isPriming = true;
    unsigned long startTime = millis();
    while (isPriming && millis() - startTime < 120000) { 
        ledcWrite(PUMP_PWM_CHANNEL, 255); 
        
        if (Serial.available() > 0) {
            char command = Serial.read();
            if (command == 'x') {
                stopPriming();
                break;
            }
        }
        delay(100); 
    }
    ledcWrite(PUMP_PWM_CHANNEL, 0); 
    if (isPriming) { 
        Serial.println("Priming Finished");
    }
}

void stopPriming() {
    ledcWrite(PUMP_PWM_CHANNEL, 0);
    isPriming = false;
    Serial.println("Priming stopped");
}
