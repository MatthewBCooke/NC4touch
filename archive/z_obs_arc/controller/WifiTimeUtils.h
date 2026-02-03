//WifiTimeUtils.h
#ifndef WifiTimeUtils_h
#define WifiTimeUtils_h

#include <WiFi.h>
#include <time.h>


extern const char* ssid;
extern const char* password;
extern const char* ntpServer; 
extern const long gmtOffset_sec;
extern const int daylightOffset_sec;

extern unsigned long currentTs, startTs, lastSyncTs, syncDuration;
extern unsigned long startMs,lastMs, lastTs;
extern struct tm timeinfo;

void connectToWiFi();
void configureTime();
extern unsigned long getUnixTimestamp();
void printLocalTime();
#endif
