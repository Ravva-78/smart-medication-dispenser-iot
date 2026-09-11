# Technical Design & Architecture Report: Backend API & Service Layer v0.1.0
**Project**: AI-Powered Medicine Dispensing System  
**Doc ID**: `docs/06_BACKEND_API.md`  
**Status**: Architecture & Design Phase (Phase 1 In Progress)  
**Date**: July 2026  

---

## Executive Summary

The **Backend API & Service Layer** (`backend/`) acts as a thin delivery adapter exposing RESTful HTTP endpoints for camera frame ingestion, inventory state queries, OCR verification, clinical adherence metrics, and dispatched alerts.

Obeying strict **Facade Encapsulation** and **Data Contract Isolation**, the API layer contains **zero business or clinical rules**. Controllers simply delegate incoming requests to underlying subsystem facades (`InventoryManager`, `OCRManager`, `ClinicalDecisionManager`, `AlertManager`) and return standardized JSON payload contracts.

---

## 1. API Endpoints Specification

| Method | Endpoint Path | Description | Underlying Facade Method |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/inspect` | Process raw camera image frame | `Vision Pipeline` $\rightarrow$ `InventoryManager` $\rightarrow$ `ClinicalDecisionManager` |
| `GET` | `/api/v1/inventory/{strip_id}` | Query inventory state for a strip | `InventoryManager.summary(strip_id)` |
| `GET` | `/api/v1/clinical/history/{patient_id}` | Query clinical decision audit log | `ClinicalDecisionManager.get_decision_history(patient_id)` |
| `GET` | `/api/v1/clinical/metrics/{patient_id}` | Query patient adherence metrics | `ClinicalDecisionManager.get_patient_metrics(patient_id)` |
| `GET` | `/api/v1/alerts/{patient_id}` | Query dispatched alert notification history | `AlertManager.get_alert_history(patient_id)` |
| `GET` | `/api/v1/health` | System health check & context status | `DispenserAPIService.health()` |

---

## 2. Package Topology (`backend/`)

```text
backend/
├── __init__.py          # Package exports & versioning (0.1.0)
├── enums.py             # HTTPStatusCode, APIResponseCode
├── exceptions.py        # APIError hierarchy
├── models.py            # APIResponse, InspectRequest dataclasses
├── controllers.py       # InspectionController, InventoryController, ClinicalController
└── server.py            # DispenserAPIService facade
```

---

## 3. Phased Development Roadmap

- **Phase 1: Domain Contracts & Controllers** (`backend/enums.py`, `backend/models.py`, `backend/controllers.py`)
- **Phase 2: DispenserAPIService Facade** (`backend/server.py`)
- **Phase 3: Unit & Integration Tests** (`tests/test_backend_api.py`)
