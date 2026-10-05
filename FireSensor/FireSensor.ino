int flamesensor_pin = 3;
int buzzer_pin= 2;
int ledPin = 4;

void setup(){
  pinMode(flamesensor_pin, INPUT);
  pinMode(buzzer_pin, OUTPUT);
  pinMode(ledPin, OUTPUT);

  Serial.begin(9600);
}

void loop(){
  if(digitalRead(flamesensor_pin) ==00)
  {
    digitalWrite(buzzer_pin, HIGH);
    digitalWrite(ledPin, HIGH);
    Serial.println("FIRE");
    delay(5000);
  } else
  {
    digitalWrite(ledPin, LOW);
    digitalWrite(buzzer_pin, LOW);
  }
}