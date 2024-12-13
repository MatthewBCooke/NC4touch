#include <iostream>
#include <fstream>
#include <unistd.h> // for usleep
#include <fcntl.h>  // for open()
#include <gpiod.h>  // for GPIO control

#define FRAMEBUFFER_DEVICE "/dev/fb1"
#define BACKLIGHT_PIN 22 // GPIO 22 for backlight control

void set_backlight(bool state)
{
    struct gpiod_chip *chip = gpiod_chip_open_by_number(0); // Use gpiochip0
    if (!chip)
    {
        std::cerr << "Error: Failed to open GPIO chip" << std::endl;
        return;
    }

    struct gpiod_line *line = gpiod_chip_get_line(chip, BACKLIGHT_PIN);
    if (!line)
    {
        std::cerr << "Error: Failed to get GPIO line for backlight" << std::endl;
        gpiod_chip_close(chip);
        return;
    }

    if (gpiod_line_request_output(line, "lcd_test", 0) < 0)
    {
        std::cerr << "Error: Failed to set GPIO line as output" << std::endl;
        gpiod_chip_close(chip);
        return;
    }

    // Set the backlight state (1 = ON, 0 = OFF)
    gpiod_line_set_value(line, state ? 1 : 0);

    // Cleanup
    gpiod_line_release(line);
    gpiod_chip_close(chip);
}

int main()
{
    // Turn on the backlight
    set_backlight(true);
    std::cout << "Backlight turned ON." << std::endl;

    usleep(2000000); // Wait 2 seconds

    // Open the framebuffer device
    std::ofstream framebuffer(FRAMEBUFFER_DEVICE, std::ios::out | std::ios::binary);
    if (!framebuffer.is_open())
    {
        std::cerr << "Error: Could not open framebuffer device " << FRAMEBUFFER_DEVICE << std::endl;
        return 1;
    }

    // Define black color (16-bit RGB565 format)
    uint16_t black = 0x0000; // Black (R=0, G=0, B=0)

    // Clear the screen with Black
    std::cout << "Filling screen with Black..." << std::endl;
    for (int i = 0; i < 480 * 320; ++i)
    {
        framebuffer.write(reinterpret_cast<char *>(&black), sizeof(black));
    }
    framebuffer.flush();
    std::cout << "Screen should now be black." << std::endl;

    usleep(2000000); // Wait 2 seconds

    // Turn off the backlight
    set_backlight(false);
    std::cout << "Backlight turned OFF." << std::endl;

    // Close the framebuffer device
    framebuffer.close();

    return 0;
}
