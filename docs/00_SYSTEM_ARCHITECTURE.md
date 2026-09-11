# Master System Architecture Specification v1.0
**Project**: Autonomous AI-Powered Medicine Dispensing Platform  
**Doc ID**: `docs/00_SYSTEM_ARCHITECTURE.md`  
**Status**: System Architecture Specification (Production Grade)  
**Date**: July 2026  

---

## Executive Overview

The **Autonomous AI-Powered Medicine Dispensing Platform** is a distributed, event-driven software architecture designed to ensure patient safety, accurate inventory tracking, and verified clinical dose dispensing.

Rather than relying on monolithic computer vision scripts, the platform is decomposed into decoupled **Bounded Contexts** operating under strict domain contracts, Test-Driven Development (TDD) guarantees, and immutable event streams.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MASTER PIPELINE FLOW                                  │
│                                                                                 │
│  [ Camera ] ──► [ Vision Subsystem ] ──► InspectionResult                      │
│                                                 │                               │
│                                                 ▼                               │
│                                      [ Inventory Subsystem ] ──► InventoryEvent │
│                                                 │                               │
│                                                 ▼                               │
│                                      [ OCR Subsystem ] ───────► MedicineIdentity│
│                                                 │                               │
│                                                 ▼                               │
│                                 ▶▶▶ [ Clinical Decision Engine ] ◄◀◄            │
│                                                 │                               │
│                                                 ▼                               │
│                                       ComplianceDecision                        │
│                                                 │                               │
│                   ┌─────────────────────────────┼─────────────────────────────┐ │
│                   ▼                             ▼                             ▼ │
│          [ Alert Engine ]             [ Backend API / Web ]          [ Dashboard ]│
│                                                 │                               │
│                                                 ▼                               │
│                                      [ Hardware Dispenser ]                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. System Bounded Contexts & Version Matrix

| Context ID | Bounded Context Name | Package | Version | Status | Data Contract Input | Data Contract Output |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
| **00** | **Shared Core Infrastructure**| `core/` | 1.0 | ✅ Frozen | Configuration / System Calls | `Clock`, `TraceContext`, `IDGenerator` |
| **--** | **In-Process EventBus** | `events/` | 1.0 | ✅ Frozen | Event Topic Channels | Subscribed Event Payloads |
| **01** | **Computer Vision** | `app.pipeline` | 1.0 | ✅ Frozen | Camera Frame / Image Path | `InspectionResult` |
| **02** | **Inventory Subsystem** | `inventory/` | 1.0 | ✅ Frozen | `InspectionResult` | `InventoryState` & `InventoryEvent` |
| **03** | **OCR Verification** | `ocr/` | 1.0 | ✅ Frozen | Crop ROI / Image Array | `MedicineIdentity` & `OCRResult` |
| **04** | **Clinical Decision Engine** | `clinical/` | 1.0 | ✅ Frozen | `InventoryEvent` + `MedicineIdentity` | `ComplianceDecision` |
| **05** | **Alert Engine** | `alerting/` | 1.0 | ✅ Frozen | `ComplianceDecision` | `AlertMessage` |
| **06** | **Backend API & Service Layer**| `backend/`, `app/` | 1.0 | ✅ Frozen | REST Request Payloads | `APIResponse` |
| **07** | **Streamlit Dev Dashboard** | `streamlit_app.py` | 1.0 | ✅ Complete | Visual Inspections / Inputs | Interactive Diagnostics |
| **08** | **Patient React Dashboard** | `frontend/` | - | 🔮 Planned | Web UI / Real-Time Events | Visual Monitoring |
| **09** | **Hardware Controller** | `hardware/` | - | 🔮 Planned | `ComplianceDecision` | Actuator Motor Signals |



---

## 2. Master System Dependency Graph

```text
                             ┌──────────────┐
                             │    core/     │
                             └──────┬───────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                 ▼                 ▼
           ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
           │   Vision    │   │  Inventory  │   │   events/   │
           └─────────────┘   └──────┬──────┘   └─────────────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │     OCR     │
                             └──────┬──────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │  Clinical   │
                             └──────┬──────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                 ▼                 ▼
           ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
           │   Alerting  │   │   Backend   │   │  Dashboard  │
           └─────────────┘   └──────┬──────┘   └─────────────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │  Hardware   │
                             └─────────────┘
```

---

## 3. End-to-End Pipeline Data Contracts

### 3.1 Contract 1: `InspectionResult` (Vision $\rightarrow$ Inventory)
Raw, instantaneous detection output from neural networks (Model A $\rightarrow$ Model B $\rightarrow$ Model C):
- `total: int`, `present: int`, `missing: int`, `missing_indices: List[int]`, `avg_confidence: float`

### 3.2 Contract 2: `InventoryEvent` (Inventory $\rightarrow$ Downstream)
Immutable audit record emitted upon discrete strip state transitions:
- `event_id: str`, `event_type: EventType`, `delta_present: int`, `removed_slots: Tuple[int, ...]`, `is_material_change: bool`, `schema_version: str` ("1.0")

### 3.3 Contract 3: `MedicineIdentity` (OCR $\rightarrow$ Clinical Engine)
Extracted and verified medical product properties:
- `medicine_name: str`, `strength: str`, `dosage_form: str`, `batch_number: Optional[str]`, `expiry_date: Optional[str]`, `confidence: float`

### 3.4 Contract 4: `ComplianceDecision` (Clinical Engine $\rightarrow$ Alerting/Backend/Hardware/Dashboard)
Final clinical evaluation outcome:
- `decision_id: str`, `patient_id: str`, `scheduled_time: datetime`, `actual_time: datetime`, `outcome: DecisionOutcome`, `reason: str`, `actionable: bool`

---

## 4. Architectural Decision Records (ADR Suite)

- **[ADR-001: Immutable Domain Models](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-001_Immutable_Domain_Models.md)**
- **[ADR-002: Test-Driven Development Workflow](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-002_Test_Driven_Development.md)**
- **[ADR-003: Event-Driven Architecture & EventBus](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-003_Event_Driven_Architecture.md)**
- **[ADR-004: Bounded Contexts & Facade Encapsulation](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-004_Bounded_Contexts_and_Facade_Encapsulation.md)**
- **[ADR-005: Shared Core Infrastructure Package](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-005_Shared_Core_Infrastructure.md)**
- **[ADR-006: Pipeline Data Contracts & Schema Versioning](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-006_Data_Contracts.md)**
- **[ADR-007: End-to-End System Pipeline Integration Testing](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-007_End_To_End_Testing.md)**
- **[ADR-008: Clinical Decision Boundary Isolation](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-008_Clinical_Decision_Boundary.md)**
- **[ADR-009: API Contract Locking & Frontend Delivery Boundary](file:///c:/Users/nan33/OneDrive/Desktop/summer_projects/ModelA_BlisterStripDetector/docs/ADR/ADR-009_API_Contract_Locking.md)**


---

## 5. Master Documentation Blueprint

```text
docs/
├── 00_SYSTEM_ARCHITECTURE.md        (Master System Architecture Specification)
├── 01_VISION_SUBSYSTEM.md           (Computer Vision Deep Learning Models)
├── 02_INVENTORY_SUBSYSTEM.md        (Domain-Driven Inventory Tracking & State Machine)
├── 03_OCR_SUBSYSTEM.md              (OCR Extraction, Cleaning & Entity Parsing)
├── 04_CLINICAL_DECISION_ENGINE.md   (Clinical Rules, Schedules & Compliance Engine)
├── 05_ALERT_ENGINE.md               (Notification & Emergency Escalation Engine)
├── 06_BACKEND_API.md                (REST / WebSockets Service Architecture)
├── 07_PATIENT_DASHBOARD.md          (Web / Mobile Application Interface)
├── 08_HARDWARE_CONTROLLER.md        (Dispenser Actuation & Motor Control)
├── 09_DEPLOYMENT_OBSERVABILITY.md   (Docker, Logging, Metrics & CI/CD)
└── 10_FINAL_SYSTEM_REPORT.md        (Complete Project Engineering Thesis)
```
