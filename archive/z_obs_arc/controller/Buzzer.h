#ifndef Buzzer_H
#define Buzzer_H


#define BUZZER D6
#define BUZZER_VOLUME 15 

// PWM config
#define BUZZER_FREQ 12000
#define BUZZER_PWM_CHANNEL 1
#define BUZZER_RESOLUTION 8


void setupBuzzer();
void activateBuzzer();
void deactivateBuzzer();

#endif
