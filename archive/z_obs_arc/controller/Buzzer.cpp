#include "Buzzer.h"
#include <Arduino.h>


void setupBuzzer() {
    pinMode(BUZZER, OUTPUT);
    ledcAttachPin(BUZZER, BUZZER_PWM_CHANNEL); 
    ledcSetup(BUZZER_PWM_CHANNEL, BUZZER_FREQ, BUZZER_RESOLUTION); 
    ledcWrite(BUZZER_PWM_CHANNEL, 0); 
}

void activateBuzzer() {
    ledcWrite(BUZZER_PWM_CHANNEL, BUZZER_VOLUME); 
}

void deactivateBuzzer() {
    ledcWrite(BUZZER_PWM_CHANNEL, 0); 
}
