#include <DHT.h>
#include <WiFi.h>
#include <PubSubClient.h>

// -------------------------
// Pin configuration (ESP32)
// -------------------------
#define SOIL_MOISTURE_PIN 34   // ADC pin for soil sensor
#define DHTPIN 4               // Digital pin for DHT11 data
#define DHTTYPE DHT11

// -------------------------
// Wi-Fi & MQTT settings
// -------------------------
const char* ssid = "schrodinger";            // <-- enter your Wi-Fi name
const char* password = "dal_tandul";    // <-- enter your Wi-Fi password
const char* mqtt_server = "mqtt-dashboard.com";
const int mqtt_port = 1883;                   // MQTT port (non-SSL)
const char* topic = "suraj/iot/sensor/data";          // topic to publish to

WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

// -------------------------
// Connect to Wi-Fi
// -------------------------
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// -------------------------
// Reconnect to MQTT Broker
// -------------------------
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {  // Client ID
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      delay(5000);
    }
  }
}

// -------------------------
// Setup
// -------------------------
void setup() {
  Serial.begin(115200);
  dht.begin();
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);

  Serial.println("ESP32 - Soil Moisture + DHT11 + MQTT Ready");
}

// -------------------------
// Loop
// -------------------------
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // -------------------------
  // Soil Moisture Sensor
  // -------------------------
  int soilValue = analogRead(SOIL_MOISTURE_PIN);
  int soilPercent = map(soilValue, 4095, 0, 0, 100); // 4095=dry, 0=wet

  // -------------------------
  // DHT11 Sensor
  // -------------------------
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature(); // Celsius

  // -------------------------
  // Print values to Serial
  // -------------------------
  Serial.print("Soil Moisture: ");
  Serial.print(soilPercent);
  Serial.println("%");

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT11 sensor!");
  } else {
    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.print(" %\t");
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" *C");
  }

  // -------------------------
  // Publish data to MQTT
  // -------------------------
  if (!isnan(humidity) && !isnan(temperature)) {
    String payload = "{";
    payload += "\"soil\":" + String(soilPercent) + ",";
    payload += "\"humidity\":" + String(humidity) + ",";
    payload += "\"temperature\":" + String(temperature);
    payload += "}";

    Serial.print("Publishing to MQTT: ");
    Serial.println(payload);
    client.publish(topic, payload.c_str());
  }

  delay(2000); // publish every 5 seconds
}
