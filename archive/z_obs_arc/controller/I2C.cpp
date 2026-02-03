#include "I2C.h"
#define DEBUG

//#define MAX_IMAGES 20 

byte i2cAddr[8];
int nDevices = 0;
unsigned long lastI2CScanMs, i2cScanDurationMs = 10000;
bool i2c_allow = false;
bool isTrainingActive= false;
byte img_id = 1;
int resp;
// TODO: Make these enum
int CMD_SHOW = 6;
int CMD_BLACK = 3;
int CMD_RESET = 4;
int CMD_IMG = 5;
//Choice_dir choiceDir;
const char dirStr[3] = {'L', 'R'};
char correctDir;


void setupI2C() {
    i2c_allow = true;
    Wire.begin();
    i2cScanner();
}



void i2cScanner() {
  // https://learn.adafruit.com/scanning-i2c-addresses/arduino
   byte error, address;

  Serial.println("Scanning...");

  nDevices = 0;
  for(address = 1; address < 8; address++ ) 
  {

    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0)
    {
      Serial.print("I2C device found at address 0x");
      if (address<16) 
        Serial.print("0");
      Serial.print(address,HEX);
      Serial.println("  !");

      i2cAddr[nDevices] = address;

      nDevices++;
    }
    else if (error==4) 
    {
      Serial.print("Unknown error at address 0x");
      if (address<16) 
        Serial.print("0");
      Serial.println(address,HEX);
    }    
  }
  if (nDevices == 0)
    Serial.println("No I2C devices found\n");
  else
    Serial.println("done\n");

  delay(500);
}
//
void receiveEvent(int howMany)
{
  if(0 < Wire.available()) {
    int x = Wire.read();    // receive byte as an integer
    Serial.println(x);

  }
}

void sendCmd(int cmd, int m0_id){
  Wire.beginTransmission(m0_id);
  Wire.write(cmd);
  Wire.endTransmission();
  //Serial.println(String(cmd) + " sent to M0 " + String(m0_id));
}



void ResponseFromRightM0(){
    resp = 0x00;
  while(resp == 0x00) {

    Wire.requestFrom(RIGHT_M0_ADDR , 1);
    if(Wire.available() > 0) {
      resp = Wire.read();
      delay(5);
      Serial.println("Acknowledgement from M0 2");
break;
    }
  }

}


void ResponseFromLeftM0(){
    resp = 0x00;
  while(resp == 0x00) {

    Wire.requestFrom(LEFT_M0_ADDR, 1);
    if(Wire.available() > 0) {
      resp = Wire.read();
      delay(10);
      Serial.println("Acknowledgement from M0 4");
break;
    }
  }

}


void sendBlackToAllM0s(void) {
    for(int i=0; i<nDevices; i++)
      {
        send_black(i2cAddr[i]);
        }
//        for(int i = 0; i < nDevices; i++) { 
//        // keep waiting until get a response rather than 0x00 from m0
//        resp = 0x00;
//        while(resp == 0x00)
//        {
//        Wire.beginTransmission(i2cAddr[i]);
//        Wire.requestFrom(i2cAddr[i], 1);
//          if(Wire.available() > 0)
//          {
//              resp = Wire.read();
//            
//              delay(10);
//              Serial.println("Black Response from M0 " + String(i2cAddr[i]));
//
//          }
//        }
//        Wire.endTransmission();
//      }

}


void i2c_send_img(String img_id, int m0_id, int len)
{
  byte data[len];
  img_id.getBytes(data, len);
  for(int i=0; i<len; i++)
  //Serial.println("Byte " + String(i) + ": " + data[i]);  
  Wire.beginTransmission(m0_id);
  Wire.write(data, len);
  Wire.endTransmission();
  Serial.println("IMG: " + img_id + " sent to M0 " + String(m0_id));
}



void send_black(byte m0_id)
{
  Wire.beginTransmission(m0_id);
  Wire.write(CMD_BLACK);
  Wire.endTransmission();
  //Serial.println("Black command sent to M0 " + String(m0_id));
}
