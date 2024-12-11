#include <SD.h>
#include "DFRobot_GDL.h"

/***************************************************************************************
** Function name:           Support functions for drawBMP()
** Descriptions:            Read 16- and 32-bit types from the SD card file
***************************************************************************************/
uint16_t read16(File&);
uint32_t read32(File&);

/***************************************************************************************
** Function name:           drawBMP
** Descriptions:            draw a BMP format bitmap to the screen
***************************************************************************************/
void drawBMP(DFRobot_GDL*, const char *, int , int , boolean );
void drawBMP8(DFRobot_GDL*, const char *, int , int , boolean );
