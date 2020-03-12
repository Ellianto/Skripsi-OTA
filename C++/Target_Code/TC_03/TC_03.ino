#define RED_LED_PIN D1
#define GREEN_LED_PIN D2

//Blink Green LED with a period of 2s

void setup() {
  // put your setup code here, to run once:
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
}

void loop() {
  // put your main code here, to run repeatedly:
  digitalWrite(RED_LED_PIN, HIGH);
  digitalWrite(GREEN_LED_PIN, HIGH);
  delay(1000);
  digitalWrite(GREEN_LED_PIN, LOW);
  delay(1000);
}
