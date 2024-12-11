// LED.h
#ifndef LED_H
#define LED_H

#define RewardLED D10
#define HouseLED D11

#define REWARDLED_BRIGHTNESS 60
#define HouseLED_BRIGHTNESS 100


// PWM config
#define REWARDLED_FREQ 5000
#define REWARDLED_PWM_CHANNEL 2
#define REWARDLED_RESOLUTION 8


#define HouseLED_FREQ 5000
#define HouseLED_PWM_CHANNEL 3
#define HouseLED_RESOLUTION 8

extern unsigned long houseLEDDurationMs; 

void setupRewardLED();
void activateRewardLED();
void deactivateRewardLED();
void setupHouseLED();
void activateHouseLED();
void deactivateHouseLED();

#endif
