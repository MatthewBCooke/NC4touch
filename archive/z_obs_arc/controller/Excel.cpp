//#include "Excel.h"

#include <Arduino.h>
#include "Excel.h"

#define NUM_TRIALS 20

char trial_metadata[NUM_TRIALS][10]; // +1 for null terminator
char trial_data[NUM_TRIALS][3][4];   

void extract_trial(const char* raw_data) {
    int trialIndex = 0;
    int dataLength = strlen(raw_data);
    int j = 0; // Declare j here

    Serial.println("Extracting trials...");
    for (int i = 0; i < dataLength && trialIndex < NUM_TRIALS; i++) {
        if (raw_data[i] == ' ' || raw_data[i] == '\0' || raw_data[i] == '\n') {
            if (j > 0) {
                trial_metadata[trialIndex][j] = '\0'; // Null-terminate the string
                trialIndex++;
                j = 0;
            }
        } else {
            if (j < 16) {
                trial_metadata[trialIndex][j++] = raw_data[i];
            }
        }
    }
    if (j > 0 && trialIndex < NUM_TRIALS) {
        trial_metadata[trialIndex][j] = '\0'; 
    }
}


void process_trial() {
    Serial.println("Processing trials...");
    for (int i = 0; i < NUM_TRIALS; i++) {

        // Ensure we have a full trial string
        if (strlen(trial_metadata[i]) == 7) {
            // Copy the segments of the string to the trial_data array
            strncpy(trial_data[i][0], trial_metadata[i], 3);
            trial_data[i][0][3] = '\0'; // Null-terminate

            strncpy(trial_data[i][1], trial_metadata[i] + 3, 3);
            trial_data[i][1][3] = '\0'; // Null-terminate

            strncpy(trial_data[i][2], trial_metadata[i] + 6, 1);
            trial_data[i][2][1] = '\0'; // Null-terminate


            Serial.print("Trial "); Serial.print(i + 1); Serial.print(": ");
            Serial.print(trial_data[i][0]); Serial.print(" ");
            Serial.print(trial_data[i][1]); Serial.print(" ");
            Serial.println(trial_data[i][2]);

       } 
        
    }
    Serial.println("CSV Data Processed");
}
