#include "drawBMP.h"

/***
 * Code adapted from https://github.com/Bodmer/TFT_HX8357/blob/4cef20c724aac1483325262736c6fbc81b57cb71/examples/Draw_SDCard_Bitmap/bitmap_functions.ino
*/

unsigned long startTime, duration1, duration2;

/***************************************************************************************
** Function name:           Support functions for drawBMP()
** Descriptions:            Read 16- and 32-bit types from the SD card file
***************************************************************************************/

// BMP data is stored little-endian, Arduino is little-endian too.
// May need to reverse subscript order if porting elsewhere.

uint16_t read16(File& f) {
  uint16_t result;
  ((uint8_t *)&result)[0] = f.read(); // LSB
  ((uint8_t *)&result)[1] = f.read(); // MSB
  return result;
}

uint32_t read32(File& f) {
  uint32_t result;
  ((uint8_t *)&result)[0] = f.read(); // LSB
  ((uint8_t *)&result)[1] = f.read();
  ((uint8_t *)&result)[2] = f.read();
  ((uint8_t *)&result)[3] = f.read(); // MSB
  return result;
}

/***************************************************************************************
** Function name:           drawBMP
** Descriptions:            draw a BMP format bitmap to the screen
***************************************************************************************/

// This function opens a Windows Bitmap (BMP) file and
// displays it at the given coordinates.  It's sped up
// by reading many pixels worth of data at a time
// (rather than pixel by pixel).  Increasing the buffer
// size makes loading a little faster but the law of
// rapidly diminishing speed improvements applies.
// Suggest 8 minimum and 85 maximum (3 x this value is
// stored in a byte = 255/3 max!)
// A value of 8 is only ~20% slower than 24 or 48!
// Note that 5 x this value of RAM bytes will be needed
// Increasing beyond 48 gives little benefit.
// Use integral division of TFT (or typical often used image)
// width for slightly better speed to avoid short buffer purging

void drawBMP(DFRobot_GDL *screen, const char *filename, int x, int y, boolean flip) 
{
  startTime = millis();
  const int16_t SCREEN_WIDTH = screen->width();
  const int16_t SCREEN_HEIGHT = screen->height();

  if ((x >= SCREEN_WIDTH) || (y >= SCREEN_HEIGHT)) return;

  File     bmpFile;
  int16_t  bmpWidth, bmpHeight;   // Image W+H in pixels
  uint32_t bmpImageoffset;        // Start address of image data in file
  uint32_t rowSize;               // Not always = bmpWidth; may have padding

  const int16_t NROWS = 8;

  // Check file exists and open it
  if ((bmpFile = SD.open(filename)) == NULL) {
    Serial.println(F("File not found")); // Can comment out if not needed
    return;
  }

  // Parse BMP header to get the information we need
  if (read16(bmpFile) != 0x4D42) { // BMP file signature check
    Serial.println("BMP File signature not valid");
    return;
  }

  read32(bmpFile);       // Dummy read to throw away and move on
  read32(bmpFile);       // Read & ignore creator bytes
  bmpImageoffset = read32(bmpFile); // Start of image data
  read32(bmpFile);       // Dummy read to throw away and move on
  bmpWidth  = read32(bmpFile);  // Image width
  bmpHeight = read32(bmpFile);  // Image height

  // Only proceed if we pass a bitmap file check
  if (read16(bmpFile) != 1) {
    Serial.println(F("BMP has more than one plane"));
    return;
  }

  const int16_t BYTEDEPTH = read16(bmpFile)/8;

  if ( BYTEDEPTH!=1 && BYTEDEPTH!=3 ) {
    Serial.println(F("BMP bit depth should be 8 or 24"));
    return;
  }

  if (read32(bmpFile) != 0) {
    Serial.println(F("BMP should be uncompressed"));
    return;
  }

  // BMP rows are padded (if needed) to 4-byte boundary
  rowSize = (bmpWidth * BYTEDEPTH + 3) & ~3;

  // Serial.println("bmpWidth: " + String(bmpWidth));
  // Serial.println("bmpHeight: " + String(bmpHeight));
  // Serial.println("screenWidth: " + String(SCREEN_WIDTH));
  // Serial.println("screenHeight: " + String(SCREEN_HEIGHT));
  // Serial.println("Byte depth: " + String(BYTEDEPTH));

  duration1 = millis()-startTime;

  // We might need to alter rotation to avoid tedious pointer manipulation
  // Save the current value so we can restore it later
  uint8_t rotation = screen->getRotation();
  // Use TFT SGRAM coord rotation if flip is set for 25% faster rendering
  if (flip) screen->setRotation((rotation + (flip<<2)) % 8); // Value 0-3 mapped to 4-7

  // We might need to flip and calculate new y plot coordinate
  // relative to top left corner as well...
  switch (rotation) {
    case 0:
      if (flip) y = SCREEN_HEIGHT - y - bmpHeight; break;
    case 1:
      y = SCREEN_HEIGHT - y - bmpHeight; break;
      break;
    case 2:
      if (flip) y = SCREEN_HEIGHT - y - bmpHeight; break;
      break;
    case 3:
      y = SCREEN_HEIGHT - y - bmpHeight; break;
      break;
  }

  Serial.println("Read prep took " + String(duration1) + " ms");

  // Finally we are ready to send rows of pixels, writing like this avoids slow 32 bit multiply
  uint32_t pos;
  duration1 = 0;
  duration2 = 0;
  uint8_t  sdbuffer[BYTEDEPTH * NROWS * SCREEN_HEIGHT];    // SD read pixel buffer (8 bits each R+G+B per pixel)

  for (int16_t r=0; r<bmpHeight ; r+=NROWS) {
    // startTime = millis();
    pos = bmpImageoffset + r*rowSize;
    // Seek if we need to on boundaries and arrange to dump buffer and start again
    if (bmpFile.position() != pos) bmpFile.seek(pos);
      
    // Reading bytes from SD Card
    bmpFile.read(sdbuffer, BYTEDEPTH * NROWS * bmpHeight);
    // duration1 += (millis()-startTime);

    // startTime = millis();

    // Write to screen
    if (BYTEDEPTH == 1) {
      uint8_t tftbuffer[3 * NROWS * SCREEN_HEIGHT];
      for (uint32_t sd_idx=0; sd_idx<(NROWS * bmpHeight); sd_idx++){
        tftbuffer[3*sd_idx] = sdbuffer[sd_idx];
        tftbuffer[3*sd_idx+1] = sdbuffer[sd_idx];
        tftbuffer[3*sd_idx+2] = sdbuffer[sd_idx];
      }
      screen->drawPIC(0, r, bmpHeight, NROWS, tftbuffer);
    } else if (BYTEDEPTH == 3) {
      screen->drawPIC(0, r, bmpHeight, NROWS, sdbuffer);
    }

    // duration2 += (millis()-startTime);
  } 
  // Serial.println("Read took " + String(duration1) + " ms");
  // Serial.println("Write took " + String(duration2) + " ms");

  bmpFile.close();
  screen->setRotation(rotation); // Put back original rotation
}
