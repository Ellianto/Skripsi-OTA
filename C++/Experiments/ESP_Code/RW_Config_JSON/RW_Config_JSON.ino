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

#define DEVICE_TYPE "ESP"

//Save the config.json to SPIFFS for persistent storage
bool saveConfig()
{
  StaticJsonDocument<STATIC_JSON_SIZE> doc;

  // Format based on config.json in EndDevicePython
  // TODO: Change this if the config.json is changed
  doc["gateway"] = "ota_gateway";
  doc["init_api"] = "/init/device";

  JsonObject device = doc.createNestedObject("device");
  device["id"] = "target_device_x01";
  device["type"] = DEVICE_TYPE;
  device["cluster"] = NULL;

  File configFile = SPIFFS.open(JSON_FILE_NAME, "w");
  if (!configFile)
  {
    Serial.println("Failed to open config file for writing");
    return false;
  }

  serializeJson(doc, configFile);
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
