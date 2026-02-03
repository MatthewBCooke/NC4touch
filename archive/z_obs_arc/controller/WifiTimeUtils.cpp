//WifiTimeUtils.cpp
#include "WifiTimeUtils.h"



const char* ssid = "NC4_Neurogenesis_Exposure";
const char* password = "nc4lab1434";
//const char* ssid = "TELUS0395";
//const char* password = "vwf93px6xp";
//const char* ntpServer = "STRATUM3VCH.healthbc.org";
const char* ntpServer = "ca.pool.ntp.org";
const long gmtOffset_sec = -8*60*60;
const int daylightOffset_sec = 3600;

unsigned long currentTs, startTs, lastSyncTs, syncDuration = 60;
unsigned long startMs, lastMs, lastTs;
struct tm timeinfo;

void connectToWiFi() {
    Serial.printf("Connecting to %s", ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println(" CONNECTED");
}

void configureTime() {
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
}

unsigned long getUnixTimestamp() {
    time_t now;
    if (!getLocalTime(&timeinfo)) {
        Serial.println("Failed to obtain time");
        return 0;
    }
    time(&now);
    return now;
}

void printLocalTime() {
    if (!getLocalTime(&timeinfo)) {
        Serial.println("Failed to obtain time");
        return;
    }
    Serial.println(&timeinfo, "%A, %B %d %Y %H:%M:%S");
}


// https://randomnerdtutorials.com/epoch-unix-time-esp32-arduino/
