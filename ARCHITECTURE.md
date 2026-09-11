# System Architecture & Subsystem Documentation

## 1. Overview
This repository contains a production-grade, multi-stage computer vision and event-driven inventory tracking system for medicine blister strips.

```text
Camera / Image Input
        │
        ▼
  Model A (Blister Strip Detector)
        │
  Perspective Correction (800x600 Rectification)
        │
  Model B (Pocket Bounding Box Detector)
        │
  Pocket Crop Extractor
        │
  Model C (Tablet Presence Classifier)
        │
  InspectionResult (Vision Output Dataclass)
        │
        ▼
  InventorySubsystem (Single Source of Truth)
        │
        ├── InventoryValidator (Technical & Mathematical Correctness)
        ├── InventoryState (Immutable Domain Model)
        ├── InventoryComparator (Delta Engine -> InventoryEvent)
        ├── InventoryHistory (Chronological Snapshot Log)
        └── InventoryPersistence (Storage Abstraction)
```

---

## 2. Inventory Subsystem Package (`inventory/`)

### Package Version: `0.1.0` (Development)

| Module | Purpose | Depends On | Version | Test Suite | Test Status | Module Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `inventory/enums.py` | InventoryStatus, EventType & DecisionOutcome Enums | None | 0.1.0 | `tests/test_enums.py` | 6/6 Passed | ✅ COMPLETED |
| `inventory/models.py` | InventoryMetadata, InventoryState & Snapshot Dataclasses | `enums.py`, `utils.py` | 0.1.0 | `tests/test_models.py` | 8/8 Passed | ✅ COMPLETED |
| `inventory/exceptions.py` | Domain Exception Hierarchy | None | 0.1.0 | `tests/test_exceptions.py` | 2/2 Passed | ✅ COMPLETED |
| `inventory/validator.py` | Technical & Mathematical Correctness Validation | `models.py`, `enums.py`, `exceptions.py` | 0.1.0 | `tests/test_validator.py` | 9/9 Passed | ✅ COMPLETED |
| `inventory/events.py` | InventoryEvent Dataclass | `models.py`, `enums.py`, `utils.py` | 0.1.0 | `tests/test_events.py` | 3/3 Passed | ✅ COMPLETED |
| `inventory/comparator.py` | State Transition Delta Engine | `models.py`, `enums.py`, `events.py` | 0.1.0 | `tests/test_comparator.py` | 9/9 Passed | ✅ COMPLETED |
| `inventory/utils.py` | Datetime Parsing & Formatting Utilities | None | 0.1.0 | `tests/test_utils.py` | 4/4 Passed | ✅ COMPLETED |
| `inventory/history.py` | Chronological Snapshot & Event Log | `models.py`, `enums.py`, `events.py` | 0.1.0 | `tests/test_history.py` | 4/4 Passed | ✅ COMPLETED |
| `inventory/formatter.py` | Terminal, Dict, JSON & Status Formatters | `models.py`, `enums.py`, `events.py` | 0.1.0 | `tests/test_formatter.py` | 5/5 Passed | ✅ COMPLETED |
| `inventory/persistence.py` | Storage Abstraction (Abstract & JSON) | `models.py`, `enums.py`, `exceptions.py` | 0.1.0 | `tests/test_persistence.py` | 5/5 Passed | ✅ COMPLETED |
| `inventory/decision.py` | Reserved Placeholder for Future Decision Engine | `enums.py` | 0.1.0 | N/A | Reserved | ✅ RESERVED |
| `inventory/manager.py` | InventoryManager Orchestration Facade & Pluggable StripIdentityProvider | All above | 0.1.0 | `tests/test_manager.py` | 7/7 Passed | ✅ COMPLETED |
| `tests/test_pipeline_integration.py` | E2E Pipeline to Inventory Subsystem Integration | All modules + `app.pipeline` | 0.1.0 | `tests/test_pipeline_integration.py` | 4/4 Passed | ✅ COMPLETED |

### Subsystem Completion Summary: 66 / 66 Tests Passed (100% Operational)





