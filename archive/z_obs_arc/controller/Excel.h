#ifndef Excel_h
#define Excel_h

#define NUM_TRIALS 20

#include <Arduino.h>

extern char trial_metadata[NUM_TRIALS][10]; // +1 for null terminator
extern char trial_data[NUM_TRIALS][3][4];   

void extract_trial(const char* raw_data);
void process_trial();

#endif
