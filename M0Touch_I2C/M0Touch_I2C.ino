/**
 * M0Touch_I2C - I2C-based touchscreen controller firmware
 * 
 * Implements I2C communication protocol for DFRobot M0 SAMD21 boards
 * with capacitive touchscreen displays. Replaces unreliable USB serial
 * communication with deterministic hardware-addressed I2C.
 * 
 * I2C Address Assignment (via GPIO pins):
 *   Pin 10 (bit 0) + Pin 11 (bit 1) + Pin 12 (bit 2) = Address 0x00-0x07
 *   Pins configured as INPUT_PULLUP, address = (bit pattern of LOW pins)
 * 
 * Protocol Frame Format:
 *   TX (Pi → M0): [length, command, payload..., checksum]
 *   RX (M0 → Pi): [length, response..., checksum]
 *   Checksum: Simple XOR of all bytes
 * 
 * Commands:
 *   0x01 WHOAREYOU - Request device ID → Response: "ID:M0_X"
 *   0x02 SHOW      - Turn on backlight, enable touch
 *   0x03 BLACK     - Turn off backlight, disable touch
 *   0x04 IMG       - Load image from SD card (payload: image ID string)
 *   0x05 TOUCH_POLL - Poll for touch event → Response: [status, x_hi, x_lo, y_hi, y_lo]
 * 
 * Author: OpenClaw Subagent
 * Date: 2026-02-03
 */

#include <Wire.h>
#include <SD.h>
#include <SPI.h>
#include "DFRobot_GDL.h"
#include "DFRobot_Touch.h"
#include "drawBMP.h"

// ===== Pin Definitions =====
#define TFT_DC   7
#define TFT_CS   5
#define TFT_RST  6
#define TFT_BLK  9

// I2C address configuration pins
#define ADDR_PIN_0  10  // LSB (bit 0)
#define ADDR_PIN_1  11  // bit 1
#define ADDR_PIN_2  12  // MSB (bit 2)

// ===== I2C Command Codes =====
#define CMD_WHOAREYOU   0x01
#define CMD_SHOW        0x02
#define CMD_BLACK       0x03
#define CMD_IMG         0x04
#define CMD_TOUCH_POLL  0x05

// ===== Global State =====
uint8_t boardID = 0;        // M0 identifier (0-7)
uint8_t i2cAddress = 0;     // I2C bus address (0x00-0x07)
bool showActive = false;    // True when image displayed and waiting for touch

// I2C receive buffer
#define I2C_BUFFER_SIZE 64
uint8_t i2cRxBuffer[I2C_BUFFER_SIZE];
volatile uint8_t i2cRxLength = 0;
volatile bool i2cCommandReady = false;

// I2C transmit buffer
uint8_t i2cTxBuffer[I2C_BUFFER_SIZE];
volatile uint8_t i2cTxLength = 0;
volatile bool i2cResponseReady = false;

// Touch state
bool touchDetected = false;
uint16_t touchX = 0;
uint16_t touchY = 0;

// ===== Hardware Objects =====
DFRobot_ILI9488_320x480_HW_SPI screen(TFT_DC, TFT_CS, TFT_RST);
DFRobot_Touch_GT911 touch;

// TouchPoint struct
typedef struct {
  bool isValid;
  uint16_t id;
  uint16_t x;
  uint16_t y;
  uint16_t w;
} TouchPoint;

TouchPoint tp;

// ===== Function Declarations =====
void setupI2CAddress();
void setupDisplayAndSD();
void processI2CCommand();
void pickPicture(const char* imageID);
void showPreloadedImage();
void setBlackScreen(bool backlightOn = true);
void scanTouch();
uint16_t numberTillComma(String &s);
uint8_t calculateChecksum(const uint8_t* data, uint8_t length);
void prepareResponse(const uint8_t* data, uint8_t length);
void onI2CReceive(int numBytes);
void onI2CRequest();

// ===== Setup =====
void setup() {
  // Initialize Serial for debugging (optional, can be removed in production)
  Serial.begin(115200);
  
  // Configure I2C address from GPIO pins
  setupI2CAddress();
  
  // Initialize I2C as slave
  Wire.begin(i2cAddress);
  Wire.onReceive(onI2CReceive);
  Wire.onRequest(onI2CRequest);
  
  // Initialize display and SD card
  setupDisplayAndSD();
  
  // Start with black screen, backlight off
  analogWrite(TFT_BLK, 0);
  screen.fillScreen(0x0000);
  
  Serial.print("M0 board #");
  Serial.print(boardID);
  Serial.print(" ready at I2C address 0x");
  Serial.println(i2cAddress, HEX);
}

// ===== Main Loop =====
void loop() {
  // Process received I2C commands
  if (i2cCommandReady) {
    processI2CCommand();
    i2cCommandReady = false;
  }
  
  // Scan for touch events
  scanTouch();
  
  // Small delay to prevent overwhelming the I2C bus
  delay(10);
}

// ===== I2C Address Setup =====
void setupI2CAddress() {
  // Configure address pins as inputs with pull-ups
  pinMode(ADDR_PIN_0, INPUT_PULLUP);
  pinMode(ADDR_PIN_1, INPUT_PULLUP);
  pinMode(ADDR_PIN_2, INPUT_PULLUP);
  
  // Small delay for pull-ups to stabilize
  delay(10);
  
  // Read address bits (LOW = 1, HIGH = 0 due to pull-up)
  boardID = 0;
  if (digitalRead(ADDR_PIN_0) == LOW) boardID |= (1 << 0);
  if (digitalRead(ADDR_PIN_1) == LOW) boardID |= (1 << 1);
  if (digitalRead(ADDR_PIN_2) == LOW) boardID |= (1 << 2);
  
  // I2C address is same as board ID (0x00-0x07)
  i2cAddress = boardID;
}

// ===== Display & SD Setup =====
void setupDisplayAndSD() {
  // Initialize GT911 touch controller
  touch.begin();
  
  // Initialize TFT display
  screen.begin();
  screen.setColorMode(COLOR_MODE_RGB565);
  
  // Initialize SD card
  while (!SD.begin()) {
    Serial.println("SD init failed, retrying...");
    delay(1000);
  }
  Serial.println("SD init success!");
}

// ===== I2C Handlers =====

/**
 * I2C Receive Handler (called when Pi sends data)
 * Receives command frame: [length, command, payload..., checksum]
 */
void onI2CReceive(int numBytes) {
  if (numBytes < 3) {
    // Minimum frame: length + command + checksum
    while (Wire.available()) Wire.read(); // Flush
    return;
  }
  
  // Read all bytes into buffer
  i2cRxLength = 0;
  while (Wire.available() && i2cRxLength < I2C_BUFFER_SIZE) {
    i2cRxBuffer[i2cRxLength++] = Wire.read();
  }
  
  // Validate checksum
  if (i2cRxLength < 3) return;
  
  uint8_t receivedChecksum = i2cRxBuffer[i2cRxLength - 1];
  uint8_t calculatedChecksum = calculateChecksum(i2cRxBuffer, i2cRxLength - 1);
  
  if (receivedChecksum != calculatedChecksum) {
    Serial.println("Checksum error!");
    return;
  }
  
  // Valid command received
  i2cCommandReady = true;
}

/**
 * I2C Request Handler (called when Pi reads from us)
 * Sends prepared response or empty response
 */
void onI2CRequest() {
  if (i2cResponseReady && i2cTxLength > 0) {
    // Send prepared response
    Wire.write(i2cTxBuffer, i2cTxLength);
    i2cResponseReady = false;
    i2cTxLength = 0;
  } else {
    // No data ready, send length = 0
    Wire.write(0x00);
  }
}

// ===== Checksum Calculation =====
uint8_t calculateChecksum(const uint8_t* data, uint8_t length) {
  uint8_t checksum = 0;
  for (uint8_t i = 0; i < length; i++) {
    checksum ^= data[i];
  }
  return checksum;
}

// ===== Prepare Response =====
void prepareResponse(const uint8_t* data, uint8_t length) {
  if (length > I2C_BUFFER_SIZE - 2) {
    length = I2C_BUFFER_SIZE - 2; // Leave room for length and checksum
  }
  
  i2cTxBuffer[0] = length; // Length byte
  memcpy(&i2cTxBuffer[1], data, length);
  
  // Calculate and append checksum (XOR of length + data)
  uint8_t checksum = calculateChecksum(i2cTxBuffer, length + 1);
  i2cTxBuffer[length + 1] = checksum;
  
  i2cTxLength = length + 2; // length + data + checksum
  i2cResponseReady = true;
}

// ===== Command Processing =====
void processI2CCommand() {
  // Frame format: [length, command, payload..., checksum]
  // i2cRxBuffer[0] = length byte (sent separately in I2C)
  // i2cRxBuffer[1] = command
  // i2cRxBuffer[2..n-1] = payload
  // i2cRxBuffer[n] = checksum (already validated)
  
  if (i2cRxLength < 2) return;
  
  uint8_t frameLength = i2cRxBuffer[0];
  uint8_t command = i2cRxBuffer[1];
  
  switch (command) {
    case CMD_WHOAREYOU: {
      // Respond with "ID:M0_X"
      char idString[16];
      snprintf(idString, sizeof(idString), "ID:M0_%d", boardID);
      prepareResponse((uint8_t*)idString, strlen(idString));
      
      Serial.print("WHOAREYOU -> ");
      Serial.println(idString);
      break;
    }
    
    case CMD_SHOW: {
      // Turn on backlight and enable touch
      showPreloadedImage();
      showActive = true;
      
      // Send ACK
      const char* ack = "ACK";
      prepareResponse((uint8_t*)ack, 3);
      
      Serial.println("CMD: SHOW");
      break;
    }
    
    case CMD_BLACK: {
      // Turn off backlight and disable touch
      setBlackScreen(false);
      showActive = false;
      
      // Send ACK
      const char* ack = "ACK";
      prepareResponse((uint8_t*)ack, 3);
      
      Serial.println("CMD: BLACK");
      break;
    }
    
    case CMD_IMG: {
      // Load image from SD card
      // Payload is image ID string
      if (i2cRxLength > 2) {
        uint8_t payloadLength = frameLength - 1; // command byte
        char imageID[32];
        
        // Copy payload (skip length and command bytes)
        memcpy(imageID, &i2cRxBuffer[2], payloadLength);
        imageID[payloadLength] = '\0';
        
        pickPicture(imageID);
        
        // Send ACK
        const char* ack = "ACK";
        prepareResponse((uint8_t*)ack, 3);
        
        Serial.print("CMD: IMG ");
        Serial.println(imageID);
      }
      break;
    }
    
    case CMD_TOUCH_POLL: {
      // Return touch status
      // Response format: [status, x_hi, x_lo, y_hi, y_lo]
      uint8_t touchResponse[5];
      
      if (touchDetected) {
        touchResponse[0] = 1; // Touch detected
        touchResponse[1] = (touchX >> 8) & 0xFF;  // X high byte
        touchResponse[2] = touchX & 0xFF;         // X low byte
        touchResponse[3] = (touchY >> 8) & 0xFF;  // Y high byte
        touchResponse[4] = touchY & 0xFF;         // Y low byte
        
        // Clear touch flag after reporting
        touchDetected = false;
      } else {
        touchResponse[0] = 0; // No touch
        touchResponse[1] = 0;
        touchResponse[2] = 0;
        touchResponse[3] = 0;
        touchResponse[4] = 0;
      }
      
      prepareResponse(touchResponse, 5);
      break;
    }
    
    default:
      Serial.print("Unknown command: 0x");
      Serial.println(command, HEX);
      break;
  }
}

// ===== Image Handling =====
void pickPicture(const char* imageID) {
  // Turn backlight off while loading
  analogWrite(TFT_BLK, 0);
  
  char filePath[32];
  snprintf(filePath, sizeof(filePath), "/%s.BMP", imageID);
  
  if (SD.exists(filePath)) {
    drawBMP(&screen, filePath, 0, 0, 1);
    Serial.print("Preloaded image: ");
    Serial.println(filePath);
  } else {
    Serial.print("Failed to open: ");
    Serial.println(filePath);
  }
}

void showPreloadedImage() {
  analogWrite(TFT_BLK, 255);
  Serial.println("Backlight on; image visible now.");
}

void setBlackScreen(bool backlightOn) {
  if (backlightOn) {
    analogWrite(TFT_BLK, 255);
  } else {
    analogWrite(TFT_BLK, 0);
  }
  screen.fillScreen(0x0000);
}

// ===== Touch Scanning =====
void scanTouch() {
  // Read from GT911 touch controller
  String scan_s = touch.scan();
  tp.id = numberTillComma(scan_s);
  tp.x  = numberTillComma(scan_s);
  tp.y  = numberTillComma(scan_s);
  tp.w  = numberTillComma(scan_s);
  
  // Validate touch point
  if (tp.id == 255 || tp.id == -1 || tp.x < 10 || tp.x > 310 || tp.y < 10 || tp.y > 470) {
    tp.isValid = false;
  } else {
    tp.isValid = true;
  }
  
  // Only process valid touches when showActive is true
  if (!tp.isValid || !showActive) return;
  
  // Valid touch detected
  touchDetected = true;
  touchX = tp.x;
  touchY = tp.y;
  
  Serial.print("TOUCH: X=");
  Serial.print(tp.x);
  Serial.print(", Y=");
  Serial.println(tp.y);
  
  // Disable further touches until next SHOW command
  showActive = false;
  
  // Turn off backlight immediately
  analogWrite(TFT_BLK, 0);
}

// ===== Utility Functions =====
uint16_t numberTillComma(String &s) {
  int commaIdx = s.indexOf(',');
  if (commaIdx == -1) {
    return (uint16_t)(-1);
  }
  int val = s.substring(0, commaIdx).toInt();
  s = s.substring(commaIdx + 1);
  return val;
}
