Skip to content
Search or jump to…
Pull requests
Issues
Marketplace
Explore
 
@vismay-s 
vismay-s
/
Arduino-and-IoT
Public
Code
Issues
Pull requests
Actions
Projects
Wiki
Security
Insights
Settings
Arduino-and-IoT/Overload_sensing_Code.ino
@vismay-s
vismay-s Add files via upload
Latest commit 4abd691 on Aug 10, 2020
 History
 1 contributor
76 lines (62 sloc)  1.98 KB


//VISMAY Sudra
#define BLYNK_PRINT Serial


#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#define TRIGGERPIN D3
#define ECHOPIN    D2
// You should get Auth Token in the Blynk App.
// Go to the Project Settings (nut icon).
char auth[] = "9eNmGkv#############"; //authorization pin

// Your WiFi credentials.
// Set password to "" for open networks.
char ssid[] = "wifi name"; //wifi name
char pass[] = "123456789"; //wifi password

WidgetLCD lcd(V1);
WidgetLED led1(V2);
BlynkTimer timer;

// V1 LED Widget is blinking
void blinkLedWidget()  // function for switching off and on LED
{
  if (led1.getValue()) {
    led1.off();
    //Serial.println("LED on V1: off");
  } else {
    led1.on();
   // Serial.println("LED on V1: on");
  }
}


void setup()
{
  // Debug console
  Serial.begin(9600);
pinMode(TRIGGERPIN, OUTPUT);
  pinMode(ECHOPIN, INPUT);
  Blynk.begin(auth, ssid, pass);
   timer.setInterval(1000L, blinkLedWidget);
  // You can also specify server:
  //Blynk.begin(auth, ssid, pass, "blynk-cloud.com", 8442);
  //Blynk.begin(auth, ssid, pass, IPAddress(192,168,1,100), 8442);

  lcd.clear(); //Use it to clear the LCD Widget
  lcd.print(0, 0, "Distance in cm"); // use: (position X: 0-15, position Y: 0-1, "Message you want to print")
  // Please use timed events when LCD printintg in void loop to avoid sending too many commands
  // It will cause a FLOOD Error, and connection will be dropped
}

void loop()
{
  lcd.clear();
  lcd.print(0, 0, "Distance in cm"); // use: (position X: 0-15, position Y: 0-1, "Message you want to print")
  long duration, distance;
  digitalWrite(TRIGGERPIN, LOW);  
  delayMicroseconds(3); 
  
  digitalWrite(TRIGGERPIN, HIGH);
  delayMicroseconds(12); 
  
  digitalWrite(TRIGGERPIN, LOW);
  duration = pulseIn(ECHOPIN, HIGH);
  distance= duration*0.034/2;
  Serial.print(distance);
  Serial.println("Cm");
  lcd.print(7, 1, distance);
  Blynk.run();
   timer.run();

  delay(2500);
  

}
© 2022 GitHub, Inc.
Terms
Privacy
Security
Status
Docs
Contact GitHub
Pricing
API
Training
Blog
About
Loading complete
