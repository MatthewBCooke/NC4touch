#pragma once

#include <pigpio.h>
#include <iostream>
#include <unistd.h>
#include <cstring>

#include "CommonTypes.h"


// Define GPIO for LCD screen
constexpr int DCRS{ 25 };  // Command: Low/ Data: High
constexpr int RESET{ 23 };  // Low -> Reset

// Define GPIO for Touch Screen
constexpr int IRQ_TOUCH{ 5 }; // Low -> Screen touched 

// Define GPIO for backlight
#define BACKLIGHT_PIN 22

// Spi Definition
constexpr int BAUDRATE_LCD{ 20000000 }; // 20 MHz
constexpr int BAUDRATE_TOUCH{ 50000 };  // 50KHz

constexpr int SPIFLAGS{ 0 }; // bits defined in pigpio's documentation

constexpr int SPICHAN_LCD{ 0 }; // Channel 0 or 1
constexpr int SPICHAN_TOUCH{ 1 }; 

// Pixels dimension
constexpr int WIDTH{ 480 };
constexpr int HEIGHT{ 320 };


// Command at the section 5 of the datasheet (http://www.lcdwiki.com/res/MSP3520/ILI9488%20Data%20Sheet.pdf)
enum class LCDCommand{
    NOP = 0x0,
    SOFTWARE_RST,
    READ_DISPLAY_IDENTIFICATION_INFO    = 0x04,
    SLEEP_IN                            = 0x10,
    SLEEP_OUT,
    NORMAL_DISPLAY_MODE_ON              = 0x13,
    DISPLAY_INVERSION_OFF               = 0x20,
    ALL_PIXEL_OFF                       = 0x22,
    ALL_PIXEL_ON,
    DISPLAY_OFF                         = 0x28,
    DISPLAY_ON,
    COLUMN_ADDRESS_SET                  = 0x2A,
    PAGE_ADDRESS_SET,
    MEMORY_WRITE                        = 0x2C,
    TEARING_EFFECT_LINE_OFF             = 0x34,
    TEARING_EFFECT_LINE_ON,
    MEMORY_ACCESS_CONTROL               = 0x36,
    IDLE_MODE_OFF                       = 0x38,
    INTERFACE_PIXEL_FORMAT              = 0x3A,
    MEMORY_WRITE_CONTINUE               = 0x3C,
    INTERFACE_MODE_CONTROL              = 0xB0,
    FRAME_RATE_CONTROL,
    DISPLAY_INVERSION_CONTROL           = 0xB4,
    DISPLAY_FUNCTION_CONTROL            = 0xB6,
    POWER_CONTROL_1                     = 0xC0,
    POWER_CONTROL_2,
    VCOM_CONTROL                        = 0XC5,
    PGAMCTRL                            = 0xE0,     // Positive Gamma Control
    NGAMCTRL,                                       // Negative Gamma Control
    SET_IMAGE_FUNCTION                  = 0xE9,
    ADJUST_CONTROL_3                    = 0xF7,
};

enum Level{
    LOW = 0,
    HIGH
};


// This class keeps the communication between the RPi and the LCD Touchscreen
class Touch
{
    private:
        // Handle for the spi
        int m_handle{};

        // Variable that keep track of clicks. Allows single click to not consider a long press for a multiple click
        bool m_isTouched{ false };
        Click m_type{}; // Get the type of the click

        // Command to send to the LCD MCU to ask for a data
        const uint8_t m_XReadCommand{ 0xD0 };
        const uint8_t m_YReadCommand{ 0x90 };

        // Max and min of touch values
        // Values are calibrated by hands, it could be wrong on other devices
        const int MAX_TOUCH_X{ 3940 };
        const int MAX_TOUCH_Y{ 3890 };

        const int MIN_TOUCH_Y{ 200 };
        const int MIN_TOUCH_X{ 240 };
    
    public:
        Touch();
        ~Touch();

        uint16_t ReadXCoord();
        uint16_t ReadYCoord();
        bool IsTouched();

        Click GetType();

        // Function to map raw touch values to screen coordinates
        void mapToScreen(Position raw, Position& screen);

    private:
        // This method sends a configuration value to the MCU touchscreen to get information about the X and Y coordinates
        uint16_t ReadData(uint8_t command);
};

// LCD Screen ILI9488 in 4-wire SPI mode
// TODO: Revised the code to send video display without desynchronisation and artefacts
// TODO: Accelerate the display for video and add more fps
class LCDScreen
{
    private:
        // Handle that keep the spi communication
        int m_handle{};

        // Instance of the touchscreen
        Touch* m_touch{};

        // Position of each click
        Position m_touchPos{};

        // 320 height pixels * 18 bits/pixels * 480 width pixels
        unsigned char* m_drawBuffer;
        unsigned char* m_prevBuffer;


        int m_SC = 0; // Start column
        int m_SP = 0; // Start page
        int m_EC = 0; // End Column
        int m_EP = 0; // End Page
        

    public:
        LCDScreen();
        ~LCDScreen();

        // The command, based on the datasheet is succeeded by its parameters we can send with WriteData
        // For more information, we can check the available commands of the datasheet ILI9488
        void WriteCommand(LCDCommand command);
        // Write a single data
        void WriteData(uint8_t data);
        // Write a bunch of data that we minimize with a chunck size
        void WriteData(char* data, unsigned int size);
        
        // This function takes in parameter the position X and Y where we start, and the position X and Y where we finish.
        // If we send more data than the address we set, the data will be ignored
        void SetAddress(unsigned int x1, unsigned int y1, unsigned int x2, unsigned int y2);
        
        // This function clear all the screen, and the components of our screen
        // Never used for the moment
        void ClearScreen();

        // This function is used to set only one pixel with a color
        void SetPixel(int x, int y, unsigned int color);

        // Used to draw a frame of the camera without the need to touch the SetAddress function and the WriteCommand - WriteData functionw
        void DrawFrame(unsigned char* data, unsigned int size);
        void DrawFrame();

        bool TouchScreen();

        const Position GetTouchCoord();

        void SetValueBuffer(unsigned char* val, unsigned int size);
        
};


