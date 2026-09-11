# OpenAPI / REST API Specification Contract v1.0
**Project**: Autonomous AI-Powered Medicine Dispensing Platform  
**Doc ID**: `docs/API_SPECIFICATION.md`  
**Base URL**: `http://localhost:8000/api/v1`  
**Interactive Documentation**: `http://localhost:8000/docs` (Swagger UI)  

---

## Executive Summary

This API specification serves as the formal data contract between the **Backend Service Layer** and frontend client applications (React / Streamlit / Mobile App). Frontends consume these endpoints to display detection visuals, inventory states, clinical decisions, and caregiver notifications without needing access to internal Python subsystem packages.

---

## Endpoints

### 1. Health Probe (`GET /api/v1/health`)

#### Response (`200 OK`)
```json
{
  "status_code": 200,
  "success": true,
  "code": "SUCCESS",
  "data": {
    "status": "HEALTHY",
    "version": "1.0.0",
    "services": {
      "inventory": "UP",
      "ocr": "UP",
      "clinical": "UP",
      "alerting": "UP"
    }
  },
  "error_message": null
}
```

---

### 2. Inspect & Evaluate (`POST /api/v1/inspect`)

#### Request Payload
```json
{
  "strip_id": "strip_20260729_001",
  "raw_inspection": {
    "inspection_id": "insp_99",
    "image_name": "frame_02.jpg",
    "capture_time": "2026-07-29T20:00:00Z",
    "camera_id": "cam_01",
    "total": 10,
    "present": 9,
    "missing": 1,
    "missing_indices": [4],
    "avg_confidence": 0.985
  },
  "prescription": {
    "prescription_id": "rx_1001",
    "patient_id": "patient_402",
    "medicine_name": "Paracetamol",
    "strength": "500mg",
    "dosage_form": "Tablet"
  }
}
```

#### Response Payload (`200 OK`)
```json
{
  "status_code": 200,
  "success": true,
  "code": "SUCCESS",
  "data": {
    "strip_id": "strip_20260729_001",
    "inventory_state": {
      "strip_id": "strip_20260729_001",
      "total_slots": 10,
      "present_count": 9,
      "missing_count": 1,
      "occupancy_percentage": 90.0,
      "missing_slots": [4],
      "status": "TABLET_MISSING"
    },
    "inventory_event": {
      "event_id": "evt_a9b8c7d6e5",
      "event_type": "TABLET_REMOVED",
      "delta_present": -1,
      "removed_slots": [4],
      "is_material_change": true,
      "schema_version": "1.0"
    },
    "decision": {
      "decision_id": "dec_1020304050",
      "timestamp": "2026-07-29T20:00:00Z",
      "patient_id": "patient_402",
      "strip_id": "strip_20260729_001",
      "prescription_id": "rx_1001",
      "outcome": "CORRECT_DOSE",
      "reason": "Correct dose taken: Paracetamol (500mg)",
      "actionable": true,
      "schema_version": "1.0"
    }
  },
  "error_message": null
}
```

---

### 3. Patient Adherence Metrics (`GET /api/v1/clinical/metrics/{patient_id}`)

#### Response (`200 OK`)
```json
{
  "status_code": 200,
  "success": true,
  "code": "SUCCESS",
  "data": {
    "patient_id": "patient_402",
    "total_decisions": 10,
    "correct_doses": 9,
    "missed_doses": 1,
    "wrong_medicines": 0,
    "expired_medicines": 0,
    "extra_doses": 0,
    "adherence_percentage": 90.0
  },
  "error_message": null
}
```

---

### 4. Dispatched Alerts (`GET /api/v1/alerts/{patient_id}`)

#### Response (`200 OK`)
```json
{
  "status_code": 200,
  "success": true,
  "code": "SUCCESS",
  "data": {
    "alerts": [
      {
        "alert_id": "alt_001",
        "timestamp": "2026-07-29T20:00:00Z",
        "patient_id": "patient_402",
        "decision_id": "dec_1020304050",
        "severity": "CRITICAL",
        "channel": "ALARM_BUZZER",
        "title": "CRITICAL: Wrong Medicine Removed",
        "message": "Extracted 'Aspirin' != prescribed 'Paracetamol'"
      }
    ]
  },
  "error_message": null
}
```
