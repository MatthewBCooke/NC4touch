
// Punishment Incorrect Training Stage w correctontrials
#include "WifiTimeUtils.h"
#include "Buzzer.h"
#include "LED.h"
#include "Reward.h"
#include "I2C.h"
#include "IrSensor.h"
#include "Excel.h"
#include "BeamBreak.h"

#define LOCAL_BUFFER_SIZE  1024 



// Enums and Global Variables
enum ESP_modes { M_SHOWIMAGE, M_DISCRIMINATING, M_TOUCHDETECTED, M_CORRECT, M_INCORRECT, M_ITI };
int mode;
int S_INVALID = 0x97;
int BLACK = 0x98;


int currentTrialIndex = 0; 
const unsigned long ITI_DURATION_MS = 10000;
char buffer[LOCAL_BUFFER_SIZE ];
bool isCorrectionTrial = false;
int correctionTrialCounter = 0; 
const int maxCorrectionTrials = 15; // Max number of correction trials

// Variables to track beam break state
bool isFirstReward = true;

void prepareForNextImageOrEnd();
void printFreeHeap();
void largeReward();
void startITI();
void displayStimuli();
void deactivateBeamBreak();
//void listenForTouch();

void setup() {
    Serial.begin(9600);

    // Network and time setup
    connectToWiFi();
    configureTime();
    lastSyncTs = getUnixTimestamp();

    // Hardware initializations
    setupBuzzer();
    setupRewardLED();
    setupReward();
    setupHouseLED();
    setupI2C();
    init_sensor();
    setupBeamBreak();

    Serial.println("Waiting for trial data...");
    while (Serial.available() <= 0) {
        delay(100); 
    }

    // Read data from serial until newline and store it in the buffer
    int bytesRead = Serial.readBytesUntil('\n', buffer, LOCAL_BUFFER_SIZE  - 1);
    buffer[bytesRead] = '\0'; // Null-terminate the string

    // Process the received data
    extract_trial(buffer);
    delay(5);
    process_trial();

    Serial.println("Trial data preloaded.");
    delay(20);
}

void loop() {
    currentTs = getUnixTimestamp();

    // Synchronize network time 
    if ((currentTs - lastSyncTs) > syncDuration) {
        configureTime();
        lastSyncTs = currentTs;
    }

    if (Serial.available() > 0) {
        char incomingByte = Serial.peek(); 
        bool isCommand = (incomingByte == 's' || incomingByte == 'p' || incomingByte == '1' || incomingByte == 'x' || incomingByte == 't');
        if (isCommand) {
            char command = Serial.read();
            switch (command) {
                case 's': // Start training
                    isTrainingActive = true;
                    mode = M_SHOWIMAGE; 
                    currentTrialIndex = 0; 
                    isFirstReward = true;
                    isCorrectionTrial = false; 
                    //sendBlackToAllM0s();
                    break;

                case 'p': // Prime the feeding tube
                    primeFeedingTube();
                    break;

                case '1': // Activate buzzer, LED, and reward via the buzzer button
                    activateBuzzer();
                    delay(10);
                    activateRewardLED();
                    delay(10);
                    deactivateBuzzer();
                    delay(300);
                    delay(10);
                    deactivateRewardLED();
                    dispenseReward();
                    delay(1000); // Dispense reward for 1 sec
                    stopRewardDispense();
                    break;

                case 'x':
                    stopPriming();
                    break;

                case 't': 
                    sendBlackToAllM0s();
                    isTrainingActive = false;
                    Serial.println("Training stopped");
                    break;
            }
        }
    }

    if (isTrainingActive && currentTrialIndex < NUM_TRIALS) {
        if (mode == M_SHOWIMAGE) {
            printFreeHeap();
            // Preload images on M0s with backlight off
            sendCmd(CMD_IMG, LEFT_M0_ADDR);
            i2c_send_img(trial_data[currentTrialIndex][0], LEFT_M0_ADDR, 5);
            Serial.println("LEFT M0 preloaded with: " + String(trial_data[currentTrialIndex][0]));

            sendCmd(CMD_IMG, RIGHT_M0_ADDR);
            i2c_send_img(trial_data[currentTrialIndex][1], RIGHT_M0_ADDR, 5);
            Serial.println("RIGHT M0 preloaded with: " + String(trial_data[currentTrialIndex][1]));


                ResponseFromLeftM0();
                ResponseFromRightM0();

                displayStimuli();
            
        } else if (mode == M_DISCRIMINATING) {

            sensor_get_value(); 
            delay(5);
            
            if (timeoutOccurred) {
                Serial.println("No Touch Detected");
                sendBlackToAllM0s();
                timeoutOccurred = false;
                prepareForNextImageOrEnd();
                startITI();
                isCorrectionTrial = false;
            } else if (detectedTouchX > 50 && !(detectedTouchX > 830 && detectedTouchX < 1030)) {
                char detectedDir;
                if (detectedTouchX >= 60 && detectedTouchX <= 830) {
                    detectedDir = 'R'; // Right
                } else if (detectedTouchX >= 1030 && detectedTouchX <= 1765) {
                    detectedDir = 'L'; // Left
                } else {
                    return; // Ignore touches outside the specified ranges
                }

                Serial.println("Touch detected at: " + String(detectedTouchX));
                Serial.println("Direction: " + String(detectedDir));

                char correctChoice = trial_data[currentTrialIndex][2][0];
                Serial.println(correctChoice);
                if (detectedDir == correctChoice) {
                    Serial.println("Correct Choice");
                    sendBlackToAllM0s();
                    largeReward();
                    isCorrectionTrial = false; 
                    startITI();
                    
                     correctionTrialCounter = 0;
                } else {
                    Serial.println("Incorrect Choice");
                    sendBlackToAllM0s();
                    activateHouseLED();
                    Serial.println("House LED activated");
                    delay(5000); // House LED on for 5 seconds
                    deactivateHouseLED();
                    if (correctionTrialCounter < maxCorrectionTrials) {
                        isCorrectionTrial = true;
                        correctionTrialCounter++; // Increment the correction trial counter
                        Serial.println("Correction trial initiated");
                        startITI();
                    } else {
                        Serial.println("Max correction trials reached. Moving to next trial.");
                        isCorrectionTrial = false;
                        correctionTrialCounter = 0; // Reset the counter for the next trial
                         Serial.println("Starting ITI...");
                        unsigned long itiStartTime = millis();
                      while (millis() - itiStartTime < ITI_DURATION_MS) { 
                     activateBeamBreak(); 
                       delay(10);    }
                        prepareForNextImageOrEnd();
                    }
                }
            }

                }
            
         else if (mode == M_ITI) {
            startITI();
        }
    }

    activateBeamBreak();
}

void startITI() {
    Serial.println("Starting ITI...");
    unsigned long itiStartTime = millis();
    while (millis() - itiStartTime < ITI_DURATION_MS) { 
        activateBeamBreak(); 
        delay(10); 
    }
    prepareForNextImageOrEnd();
}



void displayStimuli() {
  deactivateBeamBreak();
    bool beamBroken = false;
    bool beamUnbrokenAfterBreak = false;

    // Start dispensing reward and monitor beam break
    if (isFirstReward) {
        activateRewardLED();
        dispenseReward();
        Serial.println("Dispensing first reward...");
        unsigned long startTime = millis();
        while (millis() - startTime < 1100) { 
            activateBeamBreak(); // Update sensorState
            if (sensorState == LOW && !beamBroken) {
                beamBroken = true; // Beam has been broken
                Serial.println("Beam broken.");
                deactivateRewardLED(); 
            } 


            delay(10);
        }

        while (millis() - startTime < 1100) {
            delay(10);
        }
        isFirstReward = false;
        stopRewardDispense();

          
        // Ensure LED is turned off if it wasn't already
        if (!beamUnbrokenAfterBreak) {
            Serial.println("Waiting for beam to break...");
            // Wait for the mouse to enter the food tray (beam broken)
            while (sensorState != LOW) {
                activateBeamBreak(); 
                delay(10);
            }


            deactivateRewardLED();
        }
    } else {
        // Wait for the mouse to break and unbreak the beam before showing the image
        activateRewardLED();
        Serial.println("Waiting for beam to break...");
        while (sensorState != LOW) {
            activateBeamBreak(); 
            delay(10);
        }

        Serial.println("Trial Initiated");
        deactivateRewardLED();
    }
 Serial.println("Displaying stimuli for Trial Number: " + String(currentTrialIndex + 1));
 

    sendCmd(CMD_SHOW, LEFT_M0_ADDR);
    sendCmd(CMD_SHOW, RIGHT_M0_ADDR);
    delay(10);
    mode = M_DISCRIMINATING;
}



void prepareForNextImageOrEnd() {
    if (!isCorrectionTrial) {
        currentTrialIndex++; 
    }
     
    Serial.println("Trial row completed."); 
    if (currentTrialIndex < NUM_TRIALS) {
        mode = M_SHOWIMAGE;
    } else {
        isTrainingActive = false; 
        Serial.println("Training finished!");
        currentTrialIndex = 0;
    }
}

void printFreeHeap() {
    Serial.print("Free heap: ");
    Serial.println(ESP.getFreeHeap());
}

void largeReward() {
  deactivateBeamBreak();
    bool beamBroken = false;
    activateRewardLED();  
    activateBuzzer();     
    Serial.println("Buzzer activated");
    dispenseReward();     
    Serial.println("Reward dispensed");

    unsigned long startTime = millis();  
    unsigned long buzzerEndTime = startTime + 350;  
    unsigned long rewardEndTime = startTime + 1000; 

    // Loop to control the durations and check the beam break sensor
    while (millis() - startTime < 1100) {
        unsigned long currentTime = millis();

        // Deactivate buzzer after 300 milliseconds
        if (currentTime >= buzzerEndTime) {
            deactivateBuzzer();
        }

        activateBeamBreak();  // Update sensorState
        if (sensorState == LOW && !beamBroken) {
            beamBroken = true;
            Serial.println("Beam broken during reward dispense.");
            deactivateRewardLED();  // Turn off the reward LED immediately if the beam is broken
            deactivateBeamBreak();
        }

        delay(10);
    }

    stopRewardDispense();

    // Makesure LED is turned off if it wasn't already
    if (!beamBroken) {
        Serial.println("Waiting for beam to break...");
        // Wait for the mouse to enter the food tray (beam broken)
        while (sensorState != LOW) {
            activateBeamBreak(); 
            delay(10);
        }

        Serial.println("Beam broken for reward collection.");
        deactivateRewardLED();
        deactivateBeamBreak();
    }

    mode = M_ITI; 
}
