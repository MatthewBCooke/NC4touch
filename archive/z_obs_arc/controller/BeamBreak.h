#ifndef BeamBreak_H
#define BeamBreak_H



#define SENSORPIN D12  

extern int sensorState;  
extern int lastState;
extern int reading; 
extern unsigned long lastDebounceTime;
extern unsigned long debounceDelay;


void setupBeamBreak();
void activateBeamBreak();
void deactivateBeamBreak();

#endif
