#define RED_LED_PIN D1
#define GREEN_LED_PIN D2

//Blink LEDs alternating with a period of 2s

// Only a wrapper for ease of access
// Will be run in the setup() section
void setup() {
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(GREEN_LED_PIN, HIGH);
  digitalWrite(RED_LED_PIN, LOW);
  delay(1000);

  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, HIGH);
  delay(1000);
}
