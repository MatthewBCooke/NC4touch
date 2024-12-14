// cd /home/nc4/TouchscreenApparatus/src/lcd/ILI9488_LCD_Driver_RPi
// g++ -o fill_red examples/fill_red.cpp src/lcdscreen.cpp -I./headers -lpigpio -pthread
// sudo ./fill_red
// sudo pigpiod

#include <unistd.h>
#include "LCDScreen.h"

// Color 18 bits
enum Color : unsigned int
{
    RED = 0xFF0000,        // Red color: 11111111 00000000 00000000
    DARK_RED = 0xAA0000,   // Dark red
    GREEN = 0x00FF00,      // Green color: 00000000 11111111 00000000
    BLUE = 0x0000FF,       // Blue color: 00000000 00000000 11111111
    WHITE = 0xFFFFFF,      // White color: 11111111 11111111 11111111
    BLACK = 0x000000,      // Black color
    LIGHT_GREY = 0xEEEEEE, // Light grey
    DARK_GREY = 0x999999,  // Dark grey
    YELLOW = 0xFFFF00,     // Yellow color: 11111111 11111111 00000000
};

int main()
{
    // Initialize the pigpio library
    if (gpioInitialise() < 0)
    {
        // Initialization failed
        printf("pigpio initialization failed\n");
        return 1; // Exit with an error code
    }

    // Create LCD instance
    LCDScreen *lcd1 = new LCDScreen();

    // Create draw buffer with 3 bytes per pixel (R, G, B)
    unsigned char *drawBuffer = new unsigned char[3 * (WIDTH) * (HEIGHT)];

    // Set the backlight pin as an output pin
    gpioSetMode(BACKLIGHT_PIN, PI_OUTPUT);

    // Set the backlight pin high
    gpioWrite(BACKLIGHT_PIN, 1);

    // Example: Fill the screen with a red color
    for (int y = 0; y < HEIGHT; ++y)
    {
        for (int x = 0; x < WIDTH; ++x)
        {
            unsigned int color = RED;

            // Extract RGB components from the 18-bit color
            unsigned char blue = (color >> 16) & 0xFF;
            unsigned char green = (color >> 8) & 0xFF;
            unsigned char red = color & 0xFF;

            // Set the pixel color in the buffer (RGB order)
            int index = 3 * (y * WIDTH + x);
            drawBuffer[index] = red;       // Red channel
            drawBuffer[index + 1] = green; // Green channel
            drawBuffer[index + 2] = blue;  // Blue channel
        }
    }

    // Draw the buffer to the LCD
    lcd1->DrawFrame(drawBuffer, 3 * WIDTH * HEIGHT);

    delete lcd1;
    delete drawBuffer;

    gpioTerminate();

    // Set the backlight pin low
    gpioWrite(BACKLIGHT_PIN, 0);

    return 0;
}
