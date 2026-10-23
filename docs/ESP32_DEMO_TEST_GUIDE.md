# ESP32-S3-CAM demo test guide (Antigravity / PowerShell)

Items marked **[HW]** need the physical ESP32-S3-CAM on the stand. Everything else was run or mocked on the dev machine without a camera.

## 1. Environment
- Python 3.11 with the project's dependencies. The system Python 3.11 used during development already had torch, ultralytics, opencv, streamlit, fastapi and easyocr. The repo `.venv` is empty; if you use it: `pip install -r requirements.txt`.
- Models must exist: `models/production/ModelA_v2.0.pt`, `ModelB_v2.0.pt`, `ModelC_v1.0.pt` (they are in the repo).
- OCR: EasyOCR downloads its weights on first use, so the first OCR run needs internet (not verified on your machine). If OCR is unavailable the dashboard says so and skips the clinical step; tablet counting is unaffected.

## 2. Environment variables (no secrets needed for the vision demo)
| Variable | Meaning |
|---|---|
| `ESP32_CAM_URL` | Full capture URL, e.g. `http://<esp32-ip>/capture`. |
| `ESP32_CAM_IP` | Alternative: IP only; `/capture` is appended. |

You can also type the URL into the dashboard sidebar, so setting a variable is optional. The dashboard does not use MongoDB, and the `.env` file is not read by the new code.

```powershell
$env:ESP32_CAM_URL = "http://<esp32-ip>/capture"
```

## 3. Find the camera URL [HW]
1. Power the board and open the Arduino Serial Monitor at 115200 baud.
2. The firmware prints `Waiting for capture requests at: http://<ip>/capture` once Wi-Fi and the camera are up. Use that URL.
3. The laptop must be on the same Wi-Fi network (phone hotspots sometimes block device-to-device traffic).
4. The firmware's Wi-Fi name and password are hard-coded in `esp32_camera.ino`; the board only joins that network.

## 4. Verify a real image is captured [HW]
```powershell
python -m app.camera http://<esp32-ip>/capture --save $env:TEMP\esp32_test.jpg
```
- `CAPTURE OK: 640x480 px` means a real, decodable frame arrived (VGA is what the current firmware sets).
- `CAPTURE FAILED: ...` prints the cause (timeout, unreachable, HTTP error, empty, undecodable).
- Open the saved JPEG and check the whole blister is in frame, sharp and not glared. This check is by eye.

## 5. Start the dashboard and run an inspection
```powershell
python -m streamlit run streamlit_app.py
```
1. Sidebar -> **Image Input Source** -> **📡 ESP32 Camera** (the default).
2. Check/enter the capture URL, then click **📸 Capture from ESP32**. It waits at most ~3 s to connect and ~10 s for the image, then shows an error.
3. The inspection runs automatically on the captured image.

The blister grid (rows x columns) is detected from each image; no layout is assumed. To compare against a known layout, type it in the dashboard sidebar (e.g. `5x3`) or set `EXPECTED_LAYOUT=5x3` before starting; a mismatch is then reported as CONFIG_MISMATCH. A grid that does not form clean rows and columns is reported as REVIEW_REQUIRED.

## 6. Reading the result (the "Verification state" line)
| State | Banner | Meaning |
|---|---|---|
| `VERIFIED` | green "Inventory Fully Verified", or amber "Missing N Pill(s)" | Pocket grid matches and every pocket was classified with confidence >= 0.60. Counts are as trustworthy as the model (see limits). |
| `REVIEW_REQUIRED` | red | At least one pocket's confidence is below 0.60. Counts are shown but not verified; retake the picture or check by eye. |
| `CONFIG_MISMATCH` | red | Pocket count or grid differs from the expected layout (a missed pocket or the wrong strip). |
| `NO_POCKETS` | amber | No pockets found: strip out of frame, wrong exposure, or the Model B slider too high. |
| `FAILED` | red | The inspection could not run: model not loaded, unreadable or empty image. |

Inventory/clinical steps run only for `VERIFIED`. The caption states that nothing is written to the database. OCR shows its backend name and status; an OCR result is labelled UNVERIFIED unless its status is VERIFIED.

**Known limit:** the confidence check is a safety net, not proof of accuracy. On the white-strip test image the model labelled an empty pocket "present" at 0.94 confidence, and the status was `REVIEW_REQUIRED` only because another pocket on that image scored 0.56. Always compare the result with the physical strip during the demo.

## 7. Manual upload fallback
Sidebar -> **📂 Upload Image File** and choose a JPG/PNG. A file that is not a decodable image shows an error. A CLI check also works:
```powershell
python pipeline.py "qa_testing/test_images/two eaten orange.png"
```
(The CLI opens an OpenCV window and writes an inventory JSON record and stage images under `output/`.)

## 8. Measure on your own captures
Photograph each case, add rows to a CSV like `qa_testing/test_images/truth.csv` (`file,total,present,missing,missing_cells`), then:
```powershell
python scripts/eval_counts.py path\to\your\truth.csv
```
Output separates classification accuracy from status honesty (a wrong result labelled VERIFIED counts as dishonest).
Suggested cases: full strip; 1, 2, 4 and all pockets empty; torn vs flat foil; dim light; glare; strip shifted/tilted about 10-15 degrees; a wrong-layout strip.

## 9. Diagnosing problems
| Symptom | Likely cause / next step |
|---|---|
| `Cannot reach camera` | Wrong IP, different network, board not powered. Open the URL in a browser; check the Serial Monitor. |
| `Camera timed out` | Weak Wi-Fi or the board is busy; retry, move closer to the router. |
| `HTTP 500` | Firmware could not grab/convert a frame; read the Serial Monitor errors. |
| `not a decodable image` / `too small` | Corrupt or truncated transfer; retry. If repeated, send the Serial log. |
| `INSPECTION FAILED: ... not loaded` | A model file is missing or failed to load; check the terminal for the traceback. |
| `CONFIG MISMATCH` | See which count was found; check framing and that `EXPECTED_LAYOUT` fits the strip. |
| OCR "unavailable" | EasyOCR missing or its weights could not download (offline). Not a vision failure. |
| Database errors | The dashboard does not use a database. MongoDB/Atlas is used by the API server only (DNS lookup failed on the dev machine). |

## 10. What to send back for diagnosis
- The terminal output of `python -m app.camera ... --save` (success or failure).
- The saved JPEG, plus the Serial Monitor log of one capture.
- A screenshot of the full dashboard result (metrics, banner, Verification state line).
- For a wrong result: the execution report (terminal output of `python pipeline.py <saved image>`) and what the strip actually shows.
- Anything from the dashboard's red error boxes, copied verbatim.
