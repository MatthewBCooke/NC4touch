//Reward.h
#ifndef REWARD_H
#define REWARD_H

#include <Arduino.h>

// Pin for the pump
#define E2 D2

// PWM config
#define FREQ 5000
#define PUMP_PWM_CHANNEL 0
#define RESOLUTION 8

extern bool isPriming;
extern unsigned long rewardDurationMs; 

void setupReward();
void dispenseReward(); 
void stopRewardDispense();
void primeFeedingTube();
void stopPriming();

#endif
