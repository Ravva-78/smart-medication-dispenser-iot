# Standalone ESP32-S3 Camera Firmware (Phase 1)

This folder contains the standalone camera firmware designed to initialize and test the physical **ESP32-S3 WROOM N16R8 Cam** module. This firmware validates the hardware setup (Wi-Fi, PSRAM allocation, OV2640 camera acquisition, and image capture timing) prior to backend integration.

---

## 1. Files Created
*   [`esp32_camera.ino`](file:///c:/DEV/Projects/College_Projects/ProjectWork/ProjectWork/core/hardware/esp32_camera/esp32_camera.ino): Standalone Arduino sketch containing:
    *   Pinout definitions for Freenove ESP32-S3, Seeed Studio XIAO ESP32S3, and generic ESP32-S3 CAM clones.
    *   Wi-Fi connection initialization.
    *   Automatic PSRAM detection and resolution switching (SVGA vs VGA).
    *   Cyclic JPEG image capture test printing frame size, payload bytes, and capture time to the serial monitor.

---

## 2. Board Configuration Details

### Target Chip Details
*   **MCU:** Espressif Systems ESP32-S3 Dual-Core (LX7 @ 240MHz).
*   **Flash:** 16MB (N16 configuration).
*   **PSRAM:** 8MB Octal SPI (R8 configuration).
*   **Camera Module:** Omnivision **OV2640** (2MP camera module).

### Capture Resolution & Quality
*   **Resolution:** SVGA (`800x600`) - chosen to align perfectly with the backend perspective warp dimensions ([pipeline/perspective.py](file:///c:/DEV/Projects/College_Projects/ProjectWork/ProjectWork/core/pipeline/perspective.py)) and maximize OCR readability.
*   **JPEG Quality:** `10` (Lower number = higher quality. Range: 0-63). Set to `12` if PSRAM is not detected.
*   **Frame Buffers (`fb_count`):** `2` (using double-buffering for fluid capture if PSRAM is present).
*   **PSRAM Mode:** Camera frame buffers are allocated inside the external 8MB PSRAM (`CAMERA_FB_IN_PSRAM`) to ensure that internal SRAM (320KB) is not exhausted.

---

## 3. Arduino IDE & PlatformIO Setup

### Arduino IDE Instructions
1.  **Install Arduino IDE:** (v2.x or later recommended).
2.  **Add ESP32 Board URL:**
    *   Navigate to **File > Preferences**.
    *   Add the following URL to **Additional Boards Manager URLs**:
        `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3.  **Install ESP32 Package:**
    *   Open the Boards Manager (**Tools > Board > Boards Manager**).
    *   Search for `esp32` by **Espressif Systems** and install it (v2.0.11 or later recommended).
4.  **Board Settings Selection:**
    *   Select **Board:** `ESP32S3 Dev Module`.
    *   **Port:** Select your board's active COM port.
    *   **USB CDC On Boot:** `Enabled` *(Crucial for Serial Monitor debugging via Native USB)*.
    *   **Flash Size:** `16MB (128Mb)`.
    *   **Partition Scheme:** `16MB Flash (3MB APP/9.9MB FATFS)` or `Default 4MB with spiffs`.
    *   **PSRAM:** `OPI PSRAM` *(Must be set to OPI to enable the R8 PSRAM)*.

### PlatformIO Configuration (`platformio.ini` reference)
If using PlatformIO in VS Code, create a project with this configuration:
```ini
[env:esp32s3cam]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200

build_flags =
    -DBOARD_HAS_PSRAM
    -mfix-esp32-psram-cache-issue

board_build.arduino.memory_type = qio_opi
board_build.flash_mode = qio
board_build.psram_type = opi
board_upload.flash_size = 16MB
```

---

## 4. Wiring and Hardware Setup

*   **Integrated Cam Boards (e.g., Freenove ESP32-S3 CAM, AI-Thinker S3 clone):**
    *   No external camera wiring is required. The OV2640 camera module fits directly into the onboard 24-pin FPC connector.
    *   Ensure the camera ribbon cable is inserted completely and the latch lock is secured.
*   **USB Connection:**
    *   Connect the USB cable to the port labeled **USB** or **Native** (connected directly to S3's native pins) to enable CDC serial prints.
*   **Power Requirements:**
    *   **Warning:** Powering the module via 3.3V can cause brownouts (resulting in camera probe failures). Ensure the module is supplied with stable **5V (>= 1.5A)** via the micro-USB/Type-C port.

---

## 5. Flash / Upload Procedure

1.  Open [`esp32_camera.ino`](file:///c:/DEV/Projects/College_Projects/ProjectWork/ProjectWork/core/hardware/esp32_camera/esp32_camera.ino) in Arduino IDE.
2.  Uncomment your board model near the top of the file (e.g., `#define BOARD_FREENOVE_ESP32_S3_WROOM`).
3.  Replace the WiFi credentials:
    ```cpp
    const char* ssid = "YOUR_WIFI_SSID";
    const char* password = "YOUR_WIFI_PASSWORD";
    ```
4.  Connect the board to your computer's USB port.
5.  Click the **Upload** button (right-pointing arrow).
6.  *(If compilation fails due to PSRAM)*: Verify that **Tools > PSRAM** is set to `OPI PSRAM` and **USB CDC On Boot** is `Enabled`.

---

## 6. Serial Monitor Expected Output

Open the Serial Monitor in Arduino IDE (**Tools > Serial Monitor**) and set the baud rate to **115200**. Upon pressing the EN/RST button on the board, you should see:

```text
==================================================
  MEDI-DISPENSE MK2: ESP32-S3 CAM STARTUP (PHASE 1)
==================================================
Connecting to Wi-Fi Network: MyWiFiNetwork
...
[SUCCESS] Wi-Fi Connected!
IP Address: 192.168.1.104
[INFO] PSRAM detected. Setting camera resolution to SVGA (800x600)...
[SUCCESS] Camera initialized successfully!

--- Triggering Test Image Capture ---
[SUCCESS] JPEG image captured successfully!
  Frame Size: 800 x 600
  Payload Size: 24538 bytes
  Capture Time: 182 ms
Frame buffer returned to pool. Device ready for next scan.
```

---

## 7. Camera Test Procedure

1.  Verify that the onboard status LED/Flash LED triggers briefly when the capture occurs.
2.  Watch the Serial Monitor:
    *   Verify that `Payload Size` is printed and fluctuates slightly (e.g., 20,000 - 35,000 bytes). This confirms the image is dynamic and not static blank bytes.
    *   Verify that the capture loop runs reliably every 10 seconds without resetting or printing memory panic errors.
    *   Verify that `Capture Time` is reported and falls within a healthy range (100ms - 400ms).
