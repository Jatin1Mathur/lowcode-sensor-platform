/*
 * ESP32 / M5Stack sensor client
 *
 * Reads sensor values once per cycle and POSTs them as JSON to the
 * Flask REST service (/api/readings). Failed requests are retried with
 * a growing delay; HTTP 4xx responses are logged and not retried,
 * because the payload itself was rejected.
 *
 * Libraries: WiFi, HTTPClient (ESP32 core), ArduinoJson 7, time.h (NTP)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

// ---- configuration (move to a secrets.h in real use) ----
const char* WIFI_SSID     = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* API_URL       = "http://192.168.0.10:5000/api/readings";
const char* API_KEY       = "change-me";
const char* DEVICE_ID     = "esp32-rig-01";
const unsigned long CYCLE_MS = 60000;   // one load cycle = 60 s
const int MAX_RETRIES = 3;

uint32_t cycleNo = 1;

// Replace with real ADC / I2C reads for the connected sensors.
float readSensor(const char* code) {
  if (strcmp(code, "PS1") == 0)  return analogRead(34) * (200.0f / 4095.0f);  // 0-200 bar transducer
  if (strcmp(code, "TS1") == 0)  return 35.0f + random(0, 100) / 10.0f;
  if (strcmp(code, "VS1") == 0)  return 0.5f + random(0, 20) / 100.0f;
  if (strcmp(code, "FS1") == 0)  return 6.0f + random(0, 40) / 10.0f;
  return NAN;
}

const char* SENSOR_CODES[] = {"PS1", "TS1", "VS1", "FS1"};

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConnected, IP %s\n", WiFi.localIP().toString().c_str());
  configTime(0, 0, "pool.ntp.org");   // UTC timestamps
}

String isoTimestamp() {
  struct tm t;
  if (!getLocalTime(&t)) return "";
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
  return String(buf);
}

String buildPayload() {
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["cycle"] = cycleNo;
  doc["timestamp"] = isoTimestamp();
  JsonObject readings = doc["readings"].to<JsonObject>();
  for (const char* code : SENSOR_CODES) {
    float value = readSensor(code);
    if (!isnan(value)) readings[code] = value;   // skip failed reads
  }
  String out;
  serializeJson(doc, out);
  return out;
}

bool sendPayload(const String& payload) {
  for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    HTTPClient http;
    http.begin(API_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", API_KEY);
    int status = http.POST(payload);
    String body = http.getString();
    http.end();

    if (status == 201 || status == 409) {          // 409: already stored, treat as done
      Serial.printf("Cycle %u sent (HTTP %d)\n", cycleNo, status);
      return true;
    }
    if (status >= 400 && status < 500) {           // payload rejected, don't retry
      Serial.printf("Rejected (HTTP %d): %s\n", status, body.c_str());
      return false;
    }
    Serial.printf("Attempt %d failed (HTTP %d), retrying\n", attempt, status);
    delay(1000 * attempt);
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  connectWifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  String payload = buildPayload();
  Serial.println(payload);
  sendPayload(payload);
  cycleNo++;
  delay(CYCLE_MS);
}
