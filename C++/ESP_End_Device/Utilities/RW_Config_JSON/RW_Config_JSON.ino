// Example: storing JSON configuration file in flash file system
//
// Uses ArduinoJson library by Benoit Blanchon.
// https://github.com/bblanchon/ArduinoJson
//
// Created Aug 10, 2015 by Ivan Grokhotkov.
//
// This example code is in the public domain.

#include <ArduinoJson.h>
#include "FS.h"
// It's better to use StaticJsonDocument for limited RAM devices
// You can approx. the size by pasting the JSON to https://arduinojson.org/v6/assistant/

#define STATIC_JSON_SIZE 256
#define JSON_FILE_LIMIT 512

#define JSON_FILE_NAME "/config.json"

// Only here for redundancy, the template itself should define it
#define DEVICE_TYPE "ESP"

//Save the config.json to SPIFFS for persistent storage
bool saveConfig(){
  StaticJsonDocument<STATIC_JSON_SIZE> device;

  //Modify the JSON keys and values here
  device["id"] = "target_device_x02";
  device["type"] = DEVICE_TYPE;
  device["cluster"] = "target_cluster_x01";
  device["ssid"] = "PI_GW_02";
  device["passwd"] = "teknik_komputer";
  device["tcp_gw_port"] = 6666;

  File configFile = SPIFFS.open(JSON_FILE_NAME, "w");
  if (!configFile){
    Serial.println("Failed to open config file for writing");
    return false;
  }

  serializeJson(device, configFile);
  return true;
}

// Try to re-read the config file to ensure it is correctly formatted and saved
bool loadConfig() {
  File configFile = SPIFFS.open(JSON_FILE_NAME, "r");
  if (!configFile) {
    Serial.println("Failed to open config file");
    return false;
  }

  StaticJsonDocument<STATIC_JSON_SIZE> doc;
  auto error = deserializeJson(doc, configFile);
  if (error) {
    Serial.println("Failed to parse config file");
    return false;
  } else {
    // Print to Serial to inform developer of read result
    serializeJsonPretty(doc, Serial);
    Serial.println("");
    Serial.println("");
  }

  return true;
}

void setup() {
  Serial.begin(115200);
  Serial.println("");
  delay(1000);
  Serial.println("Mounting FS...");

  if (!SPIFFS.begin()) {
    Serial.println("Failed to mount file system");
    return;
  }

  if (!saveConfig()) {
    Serial.println("Failed to save config");
  } else {
    Serial.println("Config saved");
  }
  Serial.println("");

  if (!loadConfig()) {
    Serial.println("Failed to load config");
  } else {
    Serial.println("Config loaded");
  }
}

void loop() {
}
