# ADR-002: Test-Driven Development (TDD) Workflow
**Status**: Accepted  
**Date**: July 2026  

## Context
Adding features to complex ML pipelines without rigorous testing often leads to subtle regressions, where confidence normalization breaks state comparisons or regex entity parsers fail silently on edge cases.

## Decision
Every subsystem module MUST follow strict Test-Driven Development (Red $\rightarrow$ Green $\rightarrow$ Refactor):
1. Write unit tests first in `tests/test_<module>.py`.
2. Execute the test and verify explicit failure (Red Phase).
3. Write production code in `<package>/<module>.py` to satisfy assertions (Green Phase).
4. Run full system regression test discovery (`python -m unittest discover tests`).

## Consequences
- **Positive**: 100% verified correctness before code lands. Zero false confidence.
- **Positive**: Regression protection as new bounded contexts are added.
- **Negative**: Requires writing test harness setup code upfront.
