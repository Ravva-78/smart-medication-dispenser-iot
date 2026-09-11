# ADR-001: Immutable Domain Models (`@dataclass(frozen=True)`)
**Status**: Accepted  
**Date**: July 2026  

## Context
In complex multi-stage pipelines (Vision $\rightarrow$ Inventory $\rightarrow$ OCR $\rightarrow$ Clinical Engine), passing mutable state dictionaries across module boundaries leads to side-effect bugs where a downstream component unexpectedly modifies properties used by an upstream logger, audit history, or event classifier.

## Decision
All core domain models (`InventoryState`, `InventoryEvent`, `MedicineIdentity`, `Prescription`, `DoseSchedule`, `ComplianceDecision`) MUST be declared as frozen dataclasses (`@dataclass(frozen=True)`).

## Consequences
- **Positive**: Guarantees zero unintentional side effects across execution threads. Enables thread-safe event logging.
- **Positive**: Automatically generates structural equality checks (`a == b`).
- **Negative**: Creating updated models requires instantiating new instances, requiring explicit conversion methods (`to_dict` / `from_dict`).
