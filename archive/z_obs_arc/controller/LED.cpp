// LED.cpp
#include "LED.h"
#include <Arduino.h>

unsigned long houseLEDDurationMs = 5000; 

void setupRewardLED() {
  pinMode(RewardLED, OUTPUT);
  ledcAttachPin(RewardLED, REWARDLED_PWM_CHANNEL); 
  ledcSetup(REWARDLED_PWM_CHANNEL, REWARDLED_FREQ, REWARDLED_RESOLUTION); 
  ledcWrite(REWARDLED_PWM_CHANNEL, 0);  
  
}

void activateRewardLED() {
  ledcWrite(REWARDLED_PWM_CHANNEL, REWARDLED_BRIGHTNESS);

}

void deactivateRewardLED() {
  ledcWrite(REWARDLED_PWM_CHANNEL, 0); 

}   



void setupHouseLED(){
  pinMode(HouseLED, OUTPUT);
  ledcAttachPin(HouseLED, HouseLED_PWM_CHANNEL); 
  ledcSetup(HouseLED_PWM_CHANNEL, HouseLED_FREQ, HouseLED_RESOLUTION); 
  ledcWrite(HouseLED_PWM_CHANNEL, 0);  
}


void activateHouseLED() {
  ledcWrite(HouseLED_PWM_CHANNEL, HouseLED_BRIGHTNESS);

}

void deactivateHouseLED() {
  ledcWrite(HouseLED_PWM_CHANNEL, 0); 

} 
