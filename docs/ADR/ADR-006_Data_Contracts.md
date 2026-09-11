# ADR-006: Pipeline Data Contracts & Schema Versioning
**Status**: Accepted  
**Date**: July 2026  

## Context
Exposing raw computer vision model outputs (bounding boxes, raw class IDs) to downstream business logic causes downstream breakage whenever vision models are updated or retrained.

## Decision
Inter-subsystem communication MUST occur via explicit, versioned, immutable domain dataclasses:
1. `InspectionResult` (Vision $\rightarrow$ Inventory)
2. `InventoryEvent` (Inventory $\rightarrow$ Downstream)
3. `MedicineIdentity` (OCR $\rightarrow$ Clinical)
4. `ComplianceDecision` (Clinical $\rightarrow$ Alert/Hardware/Dashboard)

All events and decisions include explicit `schema_version = "1.0"` fields.

## Consequences
- **Positive**: Complete decoupling from raw neural network payloads.
- **Positive**: Backward compatibility guarantees.
