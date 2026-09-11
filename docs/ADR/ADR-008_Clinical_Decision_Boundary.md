# ADR-008: Clinical Decision Boundary Isolation
**Status**: Accepted  
**Date**: July 2026  

## Context
Downstream delivery consumers (Alert Engine, Hardware Dispenser, Patient Dashboard) need to take actions based on clinical decisions. Allowing downstream delivery components to evaluate medical rules or drug parameters would leak business logic into delivery infrastructure.

## Decision
The **Clinical Decision Engine (`clinical/`)** is the sole producer of clinical compliance decisions. Downstream engines (`alerting/`, `hardware/`, `backend/`, `frontend/`) are strict **consumers** of immutable `ComplianceDecision` payloads and MUST NOT implement clinical rules or medical evaluation logic.

## Consequences
- **Positive**: Single Source of Truth for clinical safety and compliance.
- **Positive**: Simplifies downstream engines into pure actuators, alert dispatchers, and UI renderers.
