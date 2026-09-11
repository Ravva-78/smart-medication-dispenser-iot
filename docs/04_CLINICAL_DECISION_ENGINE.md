# Technical Design & Architecture Report: Clinical Decision Engine v1.0
**Project**: AI-Powered Medicine Dispensing System  
**Doc ID**: `docs/04_CLINICAL_DECISION_ENGINE.md`  
**Status**: Production Verified (14/14 Clinical Tests Passing - 100% Operational)  
**Date**: July 2026  

---

## Executive Summary

The **Clinical Decision Engine** (`clinical/`) is the central intelligence core of the medicine dispensing platform. While the **Inventory Subsystem** tracks *what physical state changes occurred* (`TABLET_REMOVED`, `STRIP_REPLACED`) and the **OCR Subsystem** verifies *what medicine is present* (`MedicineIdentity`), the Clinical Decision Engine determines **whether those events comply with medical safety, patient prescriptions, and dosage schedules**.

It transforms inputs (`InventoryEvent` + `MedicineIdentity` + `Prescription` + `DoseSchedule` + `Current Time`) into an immutable, audit-ready `ComplianceDecision`.

---

## 1. Problem Statement & Clinical Objectives

### 1.1 The Gap Between State Change and Clinical Safety
Tracking that a tablet was removed from pocket #5 is insufficient for patient safety:
- *Was the tablet taken at the correct prescribed time (e.g. 8:00 PM $\pm$ 30 mins)?*
- *Was the tablet taken Paracetamol 500mg, or did the patient load an incorrect drug (e.g. Ibuprofen)?*
- *Has the medicine batch expired?*
- *Did the patient take an extra un-scheduled dose?*

### 1.2 Clinical Subsystem Objectives
1. Model patient `Prescription` requirements and `DoseSchedule` time windows.
2. Evaluate clinical rules against real-time `InventoryEvent` and `MedicineIdentity` payloads.
3. Classify clinical outcomes:
   - `CORRECT_DOSE`: Right medicine + Right dosage + Removed within scheduled window.
   - `DOSE_MISSED`: Scheduled time window elapsed without tablet removal.
   - `WRONG_MEDICINE`: Removed tablet does not match prescribed drug.
   - `EXTRA_DOSE`: Tablet removed when no dose was scheduled.
   - `EXPIRED_MEDICINE`: Removed tablet is past expiry date.
4. Emit an immutable `ComplianceDecision` audit payload for Alerting, Hardware Actuation, and Dashboard modules.

---

## 2. High-Level Bounded Context Architecture

```
┌───────────────────────────┐       ┌───────────────────────────┐
│    Inventory Subsystem    │       │  OCR Verification Subsys  │
│      InventoryEvent       │       │     MedicineIdentity      │
└─────────────┬─────────────┘       └─────────────┬─────────────┘
              │                                   │
              └─────────────────┬─────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                  CLINICAL DECISION ENGINE                     │
│                                                               │
│                   ┌───────────────────────┐                   │
│                   │ClinicalDecisionManager│                   │
│                   └───────────┬───────────┘                   │
│                               │                               │
│       ┌───────────────────────┼───────────────────────┐       │
│       ▼                       ▼                       ▼       │
│┌─────────────┐        ┌───────────────┐       ┌──────────────┐│
││Prescription │        │ DoseScheduler │       │ RulesEngine  ││
│└─────────────┘        └───────────────┘       └──────┬───────┘│
│                                                      │        │
│                                                      ▼        │
│                                           ┌──────────────────┐│
│                                           │ComplianceDecision││
│                                           └──────────────────┘│
└───────────────────────────────┬───────────────────────────────┘
                                │ ComplianceDecision Payload
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    DOWNSTREAM CONSUMERS                       │
│    [ Alert Engine ]   [ Hardware Dispenser ]   [ Dashboard ]  │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Package Topology (`clinical/`)

```text
clinical/
├── __init__.py          # Package exports & versioning (1.0.0)
├── enums.py             # DecisionOutcome, RuleSeverity, ScheduleWindowStatus
├── exceptions.py        # ClinicalEngineError hierarchy
├── models.py            # Prescription, DoseSchedule, ComplianceDecision dataclasses
├── schedule.py          # DoseScheduler (Time window calculator: ON_TIME, EARLY, LATE, MISSED)
├── rules.py             # ClinicalRulesEngine (Drug match, expiry & compliance rule evaluators)
├── history.py           # ClinicalHistory (Chronological audit log & adherence metrics calculator)
└── manager.py           # ClinicalDecisionManager orchestrator facade
```

---

## 4. Phased Development Roadmap & Verification Status

```text
✓ Phase 1: Domain Contracts & Models (enums.py, models.py, exceptions.py) [COMPLETED - 3/3 Tests Passed]
✓ Phase 2: Dose Scheduler Module (clinical/schedule.py) [COMPLETED - 4/4 Tests Passed]
✓ Phase 3: Clinical Rules Engine (clinical/rules.py) [COMPLETED - 3/3 Tests Passed]
✓ Phase 4: Decision Audit History (clinical/history.py) [COMPLETED - 2/2 Tests Passed]
✓ Phase 5: Decision Manager Facade (clinical/manager.py) [COMPLETED - 1/1 Test Passed]
✓ Phase 6: End-to-End System Integration (tests/test_system_pipeline.py) [COMPLETED - 1/1 Master E2E Test Passed]
```

---

## 5. Architectural Quality Attributes

1. **Zero Raw Data Consumption**: Consumes only typed domain payloads (`InventoryEvent`, `MedicineIdentity`).
2. **Deterministic Rules**: Rules engine produces identical decision outputs for identical inputs.
3. **Auditability**: Every decision is frozen and assigned a unique `decision_id` and timestamp.
4. **Encapsulation**: External callers interact strictly through `ClinicalDecisionManager`.

---

## Appendix: Master System Verification Log Output

```text
Ran 108 tests in 6.402s

OK (66 Inventory + 28 OCR + 14 Clinical/System Pipeline Integration Tests Passed)
```
