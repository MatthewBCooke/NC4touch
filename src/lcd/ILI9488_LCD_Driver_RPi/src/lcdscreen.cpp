#include "LCDScreen.h"

//////////////////////////////////////////////////////
/////////////////// TOUCH METHOD /////////////////////
//////////////////////////////////////////////////////

Touch::Touch()
{
    // Initialize gpio pins
    if (gpioSetMode(IRQ_TOUCH, PI_INPUT) != 0)
    {
        std::cerr << "Failed to set mode on one or more pins" << std::endl;
    }
    m_handle = spiOpen(SPICHAN_TOUCH, BAUDRATE_TOUCH, SPIFLAGS);
    if (m_handle < 0)
    {
        std::cerr << "Failed to open SPI Port Touch Screen" << std::endl;
    }
}

Touch::~Touch()
{
    spiClose(m_handle);
}

bool Touch::IsTouched()
{
    // Read the IRQ pin from the LCD touchscreen
    // If LOW, the screen is touched
    if (gpioRead(IRQ_TOUCH) == LOW)
    {
        if (!m_isTouched)
        {                       // If it was not touch, before, it's press
            m_isTouched = true; // Used to touch one time
            m_type = ONE_CLICK; // A single click
            return true;        // Return true for the caller
        }
        // If it's high and m_touched is true, it was a release
    }
    else if (gpioRead(IRQ_TOUCH) == HIGH && m_isTouched)
    {
        m_isTouched = false; // So touch is false
        m_type = RELEASE;    // And the type is RELEASE

        return true;
    }
    return false;
}

Click Touch::GetType() { return m_type; }

uint16_t Touch::ReadData(uint8_t command)
{
    char txBuffer[3]{command, 0, 0};
    char rxBuffer[3]{0, 0, 0};

    spiXfer(m_handle, txBuffer, rxBuffer, 3);

    // The data to decode are in 12 bits size. We store them in a 16 bits variable
    uint16_t result{static_cast<uint16_t>(((rxBuffer[1] << 8) | rxBuffer[2]) >> 3)};
    return result;
}

uint16_t Touch::ReadXCoord()
{
    // Command for reading X coordinates
    // 0xD0 is for 12-bit X read
    return ReadData(m_XReadCommand);
}

uint16_t Touch::ReadYCoord()
{
    // Command for reading X coordinates
    // 0x90 is for 12-bit Y read
    return ReadData(m_YReadCommand);
}

void Touch::mapToScreen(Position raw, Position &screen)
{
    // The position received by the LCD MCU is the difference of voltage between VREF and GND
    // The boundary limits are written in the variable MIN_TOUCH_x and MAX_TOUCH_x
    screen.x = WIDTH - (raw.x - MIN_TOUCH_X) * WIDTH / (MAX_TOUCH_X - MIN_TOUCH_X);
    screen.y = HEIGHT - (raw.y - MIN_TOUCH_Y) * HEIGHT / (MAX_TOUCH_Y - MIN_TOUCH_Y);
}

////////////////////////////////////////////////////
/////////////////// LCD METHOD /////////////////////
////////////////////////////////////////////////////

LCDScreen::LCDScreen()
{
    // Initialize gpio pins
    if (gpioSetMode(RESET, PI_OUTPUT) != 0 ||
        gpioSetMode(DCRS, PI_OUTPUT) != 0)
    {
        std::cerr << "Failed to set mode on one or more pins" << std::endl;
    }

    m_handle = spiOpen(SPICHAN_LCD, BAUDRATE_LCD, SPIFLAGS);
    if (m_handle < 0)
    {
        std::cerr << "Failed to open SPI Port LCD Screen" << std::endl;
    }

    // Initialisation Sequence
    // Reset the LCD Screen
    gpioWrite(RESET, HIGH);
    usleep(120 * 1000); // wait 120 ms
    gpioWrite(RESET, LOW);
    usleep(120 * 1000); // wait 120 ms
    gpioWrite(RESET, HIGH);
    usleep(120 * 1000); // wait 120 ms

    // Software reset
    WriteCommand(LCDCommand::SOFTWARE_RST);
    usleep(120 * 1000);

    // 0x3A Interface Pixel Format (bit depth color space)
    WriteCommand(LCDCommand::INTERFACE_PIXEL_FORMAT);
    WriteData(0X66);

    WriteCommand(LCDCommand::TEARING_EFFECT_LINE_ON);
    WriteData(0x1);

    WriteCommand(LCDCommand::MEMORY_ACCESS_CONTROL);
    WriteData(0x20);

    WriteCommand(LCDCommand::FRAME_RATE_CONTROL);
    WriteData(0xA1);
    WriteData(0x1F);

    WriteCommand(LCDCommand::ADJUST_CONTROL_3);
    WriteData(0xA9);
    WriteData(0x51);
    WriteData(0x2C);
    WriteData(0x02);

    // 0x11 Exit Sleep Mode. (Sleep OUT)
    WriteCommand(LCDCommand::SLEEP_OUT);
    usleep(120 * 1000);

    // 0x29 Display ON.
    WriteCommand(LCDCommand::DISPLAY_ON);

    m_touch = new Touch();

    m_drawBuffer = new unsigned char[3 * (WIDTH) * (HEIGHT)];
    m_prevBuffer = new unsigned char[3 * (WIDTH) * (HEIGHT)];
}

LCDScreen::~LCDScreen()
{
    spiClose(m_handle);
    delete m_touch;

    delete[] m_drawBuffer;
    delete[] m_prevBuffer;
}

bool LCDScreen::TouchScreen()
{
    // Check if the screen was touched
    if (m_touch->IsTouched())
    {
        // Get its type
        Click type{m_touch->GetType()};
        // If it is RELEASE type, we don't calculate the coordinates and keep the coordinates of the first click
        // TODO: Calculate the release coordinates
        if (type != RELEASE)
        {
            // Get the raw touch pos(without mapping)
            Position rawTouchPos{m_touch->ReadYCoord(), m_touch->ReadXCoord()}; // The value are inverted for the screen (idk why)
            // And map them to the real pixels coordinates
            m_touch->mapToScreen(rawTouchPos, m_touchPos);
        }

        usleep(50 * 1000); // sleep for 50 ms
        return true;
    }
    return false;
}

const Position LCDScreen::GetTouchCoord() { return m_touchPos; }

void LCDScreen::WriteCommand(LCDCommand command)
{
    gpioWrite(DCRS, LOW); // LOW means we send commands to the LCD
    int success{spiWrite(m_handle, reinterpret_cast<char *>(&command), 1)};
    if (success < 0)
    {
        std::cerr << "Error: " << success << " while sending command" << std::endl;
    }
}

void LCDScreen::WriteData(uint8_t data)
{
    gpioWrite(DCRS, HIGH); // HIGH means we send data to the LCD
    int success{spiWrite(m_handle, reinterpret_cast<char *>(&data), 1)};
    if (success < 0)
    {
        std::cerr << "Error: " << success << " while sending data" << std::endl;
    }
}

void LCDScreen::WriteData(char *data, unsigned int size)
{
    gpioWrite(DCRS, HIGH);
    const int chunkSize{65536}; // Chunk size (adjust as necessary)
    int totalSent{0};

    // Loop through the data in chunks
    while (totalSent < size)
    {
        int remaining{static_cast<int>(size - totalSent)};
        int toSend{(remaining > chunkSize) ? chunkSize : remaining};

        int success{spiWrite(m_handle, data + totalSent, toSend)};

        if (success < 0)
        {
            std::cerr << "Error: " << success << " while sending data" << std::endl;
            break; // Exit loop on error
        }

        totalSent += toSend;
    }
}

void LCDScreen::SetAddress(unsigned int x1, unsigned int y1, unsigned int x2, unsigned int y2)
{
    WriteCommand(LCDCommand::COLUMN_ADDRESS_SET);
    WriteData(x1 >> 8);
    WriteData(x1);
    WriteData(x2 >> 8);
    WriteData(x2);

    m_SC = x1;
    m_EC = x2;

    if (m_SC < 0)
        m_SC = 0;
    else if (m_SC > WIDTH)
        m_SC = WIDTH;

    if (m_EC < 0)
        m_EC = 0;
    else if (m_EC > WIDTH)
        m_EC = WIDTH;

    WriteCommand(LCDCommand::PAGE_ADDRESS_SET);
    WriteData(y1 >> 8);
    WriteData(y1);
    WriteData(y2 >> 8);
    WriteData(y2);

    m_SP = y1;
    m_EP = y2;

    if (m_SP < 0)
        m_SP = 0;
    else if (m_SP > HEIGHT)
        m_SP = HEIGHT;

    if (m_EP < 0)
        m_EP = 0;
    else if (m_EP > HEIGHT)
        m_EP = HEIGHT;
}

void LCDScreen::ClearScreen()
{
    SetAddress(0, 0, WIDTH, HEIGHT); // Set the address of the entire screen
    WriteCommand(LCDCommand::MEMORY_WRITE);

    int white{0xFFFFFF};
    // And write WHITE color to all pixels
    for (int i{0}; i < WIDTH; i++)
    {
        for (int m{0}; m < HEIGHT; m++)
        {
            WriteData((white >> 16) & 0xFC);
            WriteData((white >> 8) & 0xFC);
            WriteData(white & 0xFC);
        }
    }
}

void LCDScreen::SetPixel(int x, int y, unsigned int color)
{
    // Set Address
    SetAddress(x, y, x + 1, y + 1);
    // Write pixel data
    // WriteCommand(LCDCommand::MEMORY_WRITE);  // Memory write

    uint8_t red{static_cast<uint8_t>((color >> 18) & 0x3F)};   // Extract bits 23-18 for red
    uint8_t green{static_cast<uint8_t>((color >> 10) & 0x3F)}; // Extract bits 15-10 for green
    uint8_t blue{static_cast<uint8_t>((color >> 2) & 0x3F)};   // Extract bits 7-2 for blue

    unsigned char buffer[3]{red, green, blue};
    SetValueBuffer(buffer, 3);

    // WriteData(red << 2);
    // WriteData(green << 2);
    // WriteData(blue << 2);
}

void LCDScreen::DrawFrame()
{

    SetAddress(0, 0, WIDTH, HEIGHT);
    WriteCommand(LCDCommand::MEMORY_WRITE);

    bool hasChanged = false;
    for (int i = 0; i < 3 * WIDTH * HEIGHT; i++)
    {

        if (m_drawBuffer[i] != m_prevBuffer[i])
        {
            hasChanged = true;
        }
    }

    if (hasChanged)
    {
        WriteData(reinterpret_cast<char *>(m_drawBuffer), 3 * (WIDTH) * (HEIGHT));
    }

    memcpy(m_prevBuffer, m_drawBuffer, 3 * WIDTH * HEIGHT);
}

void LCDScreen::DrawFrame(unsigned char *data, unsigned int size)
{
    SetAddress(0, 0, WIDTH, HEIGHT);
    WriteCommand(LCDCommand::MEMORY_WRITE);

    WriteData(reinterpret_cast<char *>(data), size);
}

void LCDScreen::SetValueBuffer(unsigned char *val, unsigned int size)
{
    int col = m_SC * 3;
    int row = m_SP;
    for (int i = 0; i < size; i++)
    {

        int idx = col + (WIDTH) * 3 * row;
        m_drawBuffer[idx] = val[i];
        col++;
        if (col >= m_EC * 3)
        { // 3 for RGB
            col = m_SC * 3;
            row++;
        }
        if (row >= m_EP)
        {
            break;
        }
    }
}
