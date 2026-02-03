#define I2C_EN
#define SD_EN
#define DEBUG

// Library Includes
#include <SD.h>
#include <SPI.h>
#include <Wire.h>
#include "DFRobot_GDL.h"
#include "drawBMP.h"

// Custom communication pins for TFT display
#define TFT_DC  7
#define TFT_CS  5
#define TFT_RST 6
#define TFT_BLK 9

// Command constants
int cmd = -1;
int lastCmd = -1;
const int CMD_BLACK = 3;
const int CMD_IMG = 5;
const int CMD_SHOW = 6;  

String img_str;
int imageID;
int img_id;
const int M_imageID = 1;

int mode = 0;

int status;
int INVALID = 0x97;
int BLACK = 0x98;

// Buffer to store incoming image ID bytes 
char imageIDBuffer[4];  // Updated buffer size to 4
int imageIDBufferIndex = 0;

File folder, image_file;

// M0 mainboard DMA transfer setup for screen
DFRobot_ILI9488_320x480_HW_SPI screen(/*dc=*/TFT_DC,/*cs=*/TFT_CS,/*rst=*/TFT_RST);

// I2C global setup
const int i2cAddrPin0 = 10;
const int i2cAddrPin1 = 11;
const int i2cAddrPin2 = 12;
int i2cAddr;



// Function prototypes
void requestEvent();
void receiveEvent(int howMany);
void set_black();
void cmdHandler(int cmd);
void pick_picture(const char* imageID);


// setup function
void setup() {
    // Serial setup
    Serial.begin(9600);
    // I2C setup
    #ifdef I2C_EN
    pinMode(i2cAddrPin0, INPUT_PULLUP);
    pinMode(i2cAddrPin1, INPUT_PULLUP);
    pinMode(i2cAddrPin2, INPUT_PULLUP);
     i2cAddr = (digitalRead(i2cAddrPin0) == LOW) << 2 | (digitalRead(i2cAddrPin1) == LOW) << 1 | (digitalRead(i2cAddrPin2) == LOW);
    Wire.begin(i2cAddr); 
    Wire.onRequest(requestEvent);
    Wire.onReceive(receiveEvent);
    Serial.println("Started I2C peripheral with address " + String(i2cAddr));
    #endif

    // Screen setup
    screen.begin();
    screen.setColorMode(COLOR_MODE_RGB565);

    // SD Card Setup
    #ifdef SD_EN
    while (true) {
        if (SD.begin()) {
            Serial.println("SD card initialization done.");
            break;
        }
        Serial.println("SD card initialization failed!");
    }
    folder = SD.open("/");
    #endif
}

void loop() {
    if (mode == 0) {
        if (cmd != -1) {
            cmdHandler(cmd);
            cmd = -1; 
        }
    }
}

void receiveEvent(int howMany) {
    while (Wire.available()) {
        if (lastCmd == -1) {
            lastCmd = Wire.read();
            if (lastCmd != CMD_IMG) {
                // If it's not an image command, handle it immediately
                cmdHandler(lastCmd);
                lastCmd = -1; 
            }
        } else if (lastCmd == CMD_IMG) {
            // The last command was an image command, expecting image ID bytes
            imageIDBuffer[imageIDBufferIndex++] = Wire.read();
            if (imageIDBufferIndex == 3) {  // Updated to 3
                imageIDBuffer[3] = '\0'; // Null-terminate the ID string
                pick_picture(imageIDBuffer); 
                lastCmd = -1;
                imageIDBufferIndex = 0;
            }
        }
    }
}

void cmdHandler(int lastCmd) {
    if (lastCmd == CMD_BLACK) {
        set_black();
    } else if (lastCmd == CMD_SHOW) {
        showPreloadedImage();  // Turn on backlight and show preloaded image
    }
}

// Add showPreloadedImage function
void showPreloadedImage() {
    analogWrite(TFT_BLK, 255);  
    Serial.println("Backlight activated, displaying preloaded image.");
}



void pick_picture(const char* imageID) {
    char filePath[10];
    snprintf(filePath, sizeof(filePath), "/%s.BMP", imageID);
    bool imageFileExists = SD.exists(filePath);
    if (imageFileExists) {
        analogWrite(TFT_BLK, 0);  
        drawBMP(&screen, filePath, 0, 0, 1);  // Preload image
        Serial.println("Image preloaded: " + String(filePath));
        status = M_imageID;  
    } else {
        Serial.println("Failed to open image file: " + String(filePath));
        status = INVALID;
    }
}



void requestEvent() {
    Wire.write(status);
}


void set_black() {
    analogWrite(TFT_BLK, 0);
    screen.fillScreen(COLOR_RGB565_BLACK);
    analogWrite(TFT_BLK, 255);
    status = BLACK;
}
