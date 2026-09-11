# ADR-005: Shared Core Infrastructure Package (`core/`)
**Status**: Accepted  
**Date**: July 2026  

## Context
Cross-cutting infrastructure needs (logging configuration, system clocks, ID generation, observability tracing, application configuration) were being duplicated across bounded contexts or using direct system calls (`datetime.now()`, `uuid.uuid4()`), making testing non-deterministic.

## Decision
Centralize shared cross-cutting infrastructure into a frozen `core/` package:
- `core/clock.py`: `Clock` facade with `MockClock` for time-travel testing.
- `core/ids.py`: `IDGenerator` with consistent prefix formatting.
- `core/tracing.py`: `TraceContext` for distributed correlation tracking.
- `core/config.py`: Centralized `AppConfig`.
- `core/logging.py`: Centralized logger factory.

## Consequences
- **Positive**: Eliminates duplicated utility code. Enables deterministic testing of time-sensitive schedules.
- **Negative**: All packages depend on `core/`.
