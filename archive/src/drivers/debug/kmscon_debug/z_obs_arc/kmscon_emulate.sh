modetest -M nc4_ili9488 -s 31@34:320x480
modetest -M nc4_ili9488 -P 32@34:320x480
sudo fbi -d /dev/fb0 -T 1 /home/nc4/TouchscreenApparatus/data/images/A01.bmp
sudo fbi -d /dev/fb1 -T 1 /home/nc4/TouchscreenApparatus/data/images/B01.bmp
