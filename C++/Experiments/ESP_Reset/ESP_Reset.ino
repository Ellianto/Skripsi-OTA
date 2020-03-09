
#include <ESP8266WiFi.h>

void setup() {
  // Initial Attempt
  WiFi.softAPdisconnect(true);
  WiFi.disconnect(true);

  // If not success, try these instead
  // ESP.eraseConfig();
  // ESP.reset();
}

void loop() {
  // put your main code here, to run repeatedly:

}
