# ADR-009: API Contract Locking & Frontend Delivery Boundary
**Status**: Accepted  
**Date**: July 2026  

## Context
As frontend developers build React UI components consuming the platform's REST endpoints, changing response key names or JSON data structures would break client integration.

## Decision
1. The FastAPI REST endpoints (`/api/v1/health`, `/api/v1/inspect`, `/api/v1/clinical/metrics/{patient_id}`, `/api/v1/alerts/{patient_id}`) documented in `docs/API_SPECIFICATION.md` are officially LOCKED.
2. Breaking changes to response JSON key names or payload data structures are strictly prohibited.
3. Automated API contract tests (`tests/test_api_contract.py`) MUST be run in CI/CD to prevent schema regressions.

## Consequences
- **Positive**: Guarantees a stable, reliable interface for frontend development teams.
- **Positive**: Eliminates cross-team integration friction.
