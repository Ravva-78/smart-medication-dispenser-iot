# ADR-004: Bounded Contexts & Facade Encapsulation
**Status**: Accepted  
**Date**: July 2026  

## Context
As the platform expands across Vision, Inventory, OCR, Clinical Decision, Alerting, and Hardware modules, tight coupling between internal submodules creates fragile code where internal refactoring breaks external consumers.

## Decision
1. The platform is partitioned into isolated Bounded Context packages (`inventory/`, `ocr/`, `clinical/`, etc.).
2. Each Bounded Context MUST expose exactly one primary Orchestrator Facade (`InventoryManager`, `OCRManager`, `ClinicalDecisionManager`).
3. External modules MUST NOT import internal submodules directly; all communication occurs via the subsystem Facade consuming typed domain contracts.

## Consequences
- **Positive**: Complete encapsulation. Internal submodules (cleaners, parsers, validators) can be refactored with zero ripple effects on other subsystems.
- **Positive**: Clean, readable API surfaces.
- **Negative**: Facades must maintain delegation methods.
