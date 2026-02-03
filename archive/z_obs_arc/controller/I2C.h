#ifndef I2C_h
#define I2C_h

#define RIGHT_M0_ADDR 2
#define LEFT_M0_ADDR 4


#include <Arduino.h>
#include <Wire.h>


// I2C device addresses
extern byte i2cAddr[];
extern int nDevices;
extern unsigned long lastI2CScanMs, i2cScanDurationMs;
extern bool i2c_allow;
extern bool isTrainingActive;
extern byte img_id;
extern int resp;
extern int CMD_SHOW;
extern int CMD_BLACK;
extern int CMD_IMG;
extern char correctDir;
extern const char dirStr[3];


//enum Choice_dir {
//  D_LEFT,
//  D_RIGHT,
//};

//extern Choice_dir choiceDir;

void setupI2C();
void i2cScanner();
void receiveEvent(int howMany);
void sendBlackToAllM0s();
void sendImageToAllM0s();

void i2c_send_img(String img_id, int m0_id, int len);
//void i2c_send_img(String img_id, int m0_id);
void sendCmd(int cmd, int m0_id);
void send_black(byte m0_id);
void sendResetToAllM0s();

void ResponseFromTopM0();
void ResponseFromLeftM0();
void ResponseFromRightM0();
//void listenForTouch();

#endif
