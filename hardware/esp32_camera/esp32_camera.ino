/**
 * esp32_camera.ino
 *
 * ESP32-S3 WROOM-CAM + OV2640 Firmware (Phase 3)
 * Provides a local HTTP Server to trigger one-shot captures from React.
 */

#include "esp_camera.h"
#include "img_converters.h"
#include <WiFi.h>
#include <WebServer.h>

// =====================================================
// ESP32-S3 WROOM-CAM + OV2640 PIN MAPPING
// =====================================================
#define PWDN_GPIO_NUM    -1
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM    15
#define SIOD_GPIO_NUM     4
#define SIOC_GPIO_NUM     5
#define Y9_GPIO_NUM      16
#define Y8_GPIO_NUM      17
#define Y7_GPIO_NUM      18
#define Y6_GPIO_NUM      12
#define Y5_GPIO_NUM      10
#define Y4_GPIO_NUM       8
#define Y3_GPIO_NUM       9
#define Y2_GPIO_NUM      11
#define VSYNC_GPIO_NUM    6
#define HREF_GPIO_NUM     7
#define PCLK_GPIO_NUM    13
#define LED_GPIO_NUM      2 // Onboard LED

// =====================================================
// WI-FI CONFIGURATION
// =====================================================
const char* ssid = "OnePlu43";
const char* password = "123456789";

// HTTP Server on port 80
WebServer server(80);

// Function declarations
void handleCapture();
void handleOptions();

void setup() {
  Serial.begin(115200);
  delay(2000); // 2-second delay for USB CDC serial initialization
  Serial.println("\n==================================================");
  Serial.println("  MEDI-DISPENSE MK2: ESP32-S3 CAM STARTUP (PHASE 3)");
  Serial.println("==================================================");

  // 1. Connect Wi-Fi
  Serial.printf("Connecting to Wi-Fi Network: %s\n", ssid);
  WiFi.begin(ssid, password);
  
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 10000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[SUCCESS] Wi-Fi Connected!");
    Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WARNING] Wi-Fi Connection Timeout. Running in offline mode.");
  }

  // 2. Camera Configuration (Using proven RGB565 initialization parameters)
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;

  // Initialize in RGB565 as verified by working configuration
  config.pixel_format = PIXFORMAT_RGB565;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  // 3. Initialize Camera
  Serial.println("Initializing camera...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Camera initialization failed: 0x%x\n", err);
    return;
  }
  Serial.println("[SUCCESS] Camera initialized successfully.");

  // 4. Configure WebServer Routes
  server.on("/capture", HTTP_GET, handleCapture);
  server.on("/capture", HTTP_OPTIONS, handleOptions);
  
  server.begin();
  Serial.println("[SUCCESS] HTTP server started on port 80.");
  Serial.println("Waiting for capture requests at: http://" + WiFi.localIP().toString() + "/capture");
}

void loop() {
  // Reconnect Wi-Fi if connection drops
  if (WiFi.status() != WL_CONNECTED && WiFi.localIP().toString() != "0.0.0.0") {
    Serial.print("Reconnecting to Wi-Fi...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
    unsigned long reconnectStart = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - reconnectStart < 5000) {
      delay(500);
      Serial.print(".");
    }
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\n[SUCCESS] Wi-Fi Reconnected!");
      Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
    } else {
      Serial.println("\n[WARNING] Reconnection failed. Retrying next loop.");
    }
  }

  // Handle incoming HTTP client requests
  server.handleClient();
  delay(2); // Small yield to prevent CPU starvation
}

/**
 * OPTIONS preflight handler for Private Network Access / CORS bypass
 */
void handleOptions() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.sendHeader("Access-Control-Allow-Private-Network", "true");
  server.send(204); // No content
}

/**
 * Capture frame in RGB565, convert to JPEG in software, and stream as response.
 */
void handleCapture() {
  Serial.println("\n--- Triggered Capture Request via HTTP GET ---");
  
  #ifdef LED_GPIO_NUM
    pinMode(LED_GPIO_NUM, OUTPUT);
    digitalWrite(LED_GPIO_NUM, HIGH); // Onboard LED ON
    delay(100);
  #endif

  unsigned long captureStart = millis();
  
  // 1. Grab raw RGB565 frame
  camera_fb_t *fb = esp_camera_fb_get();
  
  #ifdef LED_GPIO_NUM
    digitalWrite(LED_GPIO_NUM, LOW); // Onboard LED OFF
  #endif

  if (!fb) {
    Serial.println("[ERROR] Failed to capture raw image frame from camera sensor.");
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }

  // Store metadata locally before returning the frame buffer
  int width = fb->width;
  int height = fb->height;

  // 2. Perform software conversion to JPEG
  uint8_t *jpg_buf = NULL;
  size_t jpg_len = 0;

  bool converted = frame2jpg(
    fb,
    80,              // JPEG quality (0-100)
    &jpg_buf,
    &jpg_len
  );

  // Return the raw frame buffer immediately to prevent memory leaks
  esp_camera_fb_return(fb);

  if (!converted) {
    Serial.println("[ERROR] Software conversion from RGB565 to JPEG failed.");
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(500, "text/plain", "JPEG conversion failed");
    return;
  }

  Serial.println("[SUCCESS] Image captured and converted successfully!");
  Serial.printf("  Resolution:     %d x %d\n", width, height);
  Serial.printf("  JPEG size:      %u bytes\n", (unsigned int)jpg_len);
  Serial.printf("  Processing time: %lu ms\n", millis() - captureStart);

  // 3. Send JPEG payload with PNA & CORS headers
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.sendHeader("Access-Control-Allow-Private-Network", "true");
  
  server.setContentLength(jpg_len);
  server.send(200, "image/jpeg", "");
  server.sendContent((const char*)jpg_buf, jpg_len);

  // 4. Memory Cleanup
  free(jpg_buf);
  Serial.println("Capture resources cleared. Server ready for next request.");
}
