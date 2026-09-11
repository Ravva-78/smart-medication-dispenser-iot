# ADR-007: End-to-End System Pipeline Integration Testing
**Status**: Accepted  
**Date**: July 2026  

## Context
While unit tests verify individual modules, system regressions can occur at the integration points where outputs from one facade are passed to another.

## Decision
Maintain a dedicated end-to-end master pipeline integration test suite (`tests/test_system_pipeline.py`) that executes the complete sequence:
`InspectionResult` $\rightarrow$ `InventoryManager` $\rightarrow$ `OCRManager` $\rightarrow$ `ClinicalDecisionManager` $\rightarrow$ `ComplianceDecision`.

## Consequences
- **Positive**: Validates that all domain contracts fit together end-to-end.
- **Positive**: Highest level regression safeguard.
