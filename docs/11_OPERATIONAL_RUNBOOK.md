# Operational Runbook & Production Deployment Guide v1.0
**Project**: Autonomous AI-Powered Medicine Dispensing Platform  
**Doc ID**: `docs/11_OPERATIONAL_RUNBOOK.md`  
**Status**: Production Operational Specification  
**Date**: July 2026  

---

## Executive Overview

This operational runbook provides production deployment guidelines, startup/shutdown procedures, health monitoring endpoints, recovery workflows, and troubleshooting steps for operators of the Autonomous Medicine Dispensing Platform.

---

## 1. System Startup & Initialization Sequence

To launch the complete dispensing platform stack:

```powershell
# 1. Activate Python Virtual Environment
.\.venv311\Scripts\Activate.ps1

# 2. Run Full Automated Regression Test Discovery
python -m unittest discover tests

# 3. Initialize Shared Core Infrastructure & EventBus
# (Automatically loaded when initializing DispenserAPIService)
```

---

## 2. Health Monitoring & Observability Endpoints

| Endpoint | Method | Expected Output | Purpose |
| :--- | :---: | :--- | :--- |
| `/api/v1/health` | `GET` | `{"status": "HEALTHY", "services": {"inventory": "UP", "ocr": "UP", "clinical": "UP", "alerting": "UP"}}` | System-wide liveness and readiness probe |
| `/api/v1/clinical/metrics/{patient_id}` | `GET` | `{"patient_id": "...", "adherence_percentage": 100.0, "total_decisions": 5}` | Patient adherence metric check |
| `/api/v1/alerts/{patient_id}` | `GET` | `{"alerts": [...]}` | Audit log of dispatched caregiver notifications |

---

## 3. Recovery & Rollback Procedures

### 3.1 Corrupted Persistence State Recovery
If an inventory state JSON file becomes corrupted (e.g. invalid JSON syntax):
1. The `InventoryManager` logs an emergency warning: `Failed to load/parse inventory JSON`.
2. The subsystem automatically falls back to an in-memory `InventoryHistory` state buffer.
3. To manually repair: Locate storage directory `tests/temp_persistence_storage/<strip_id>.json` and restore from atomic `.tmp` backup buffer.

### 3.2 Low Confidence OCR Fallback
If packaging reflection or glare causes OCR extraction confidence to fall below threshold:
1. `OCRManager` sets `status = OCRStatus.UNCERTAIN`.
2. `ClinicalDecisionManager` logs an `UNCERTAIN` audit record and refrains from dispensing until verified.
3. Operator Action: Reposition lighting or manually verify strip identity via barcode lookup provider (`CustomOCRStripIdentityProvider`).

---

## 4. Production Readiness Checklist

- [x] All 117 automated unit and integration tests passing (`python -m unittest discover tests`).
- [x] Zero raw neural network predictions leaking into downstream clinical logic.
- [x] Immutable domain dataclasses enforced across all bounded contexts (`@dataclass(frozen=True)`).
- [x] Facade encapsulation verified (`InventoryManager`, `OCRManager`, `ClinicalDecisionManager`, `AlertManager`, `DispenserAPIService`).
- [x] Trace correlation IDs (`trace_id`, `strip_id`, `decision_id`) logged across all operations.
- [x] ADRs 001 through 008 documented under `docs/ADR/`.