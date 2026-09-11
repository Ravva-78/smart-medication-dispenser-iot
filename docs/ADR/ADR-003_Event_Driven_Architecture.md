# ADR-003: Event-Driven Architecture & In-Process EventBus
**Status**: Accepted  
**Date**: July 2026  

## Context
Downstream consumers (Alert Engine, Hardware Actuator, Dashboard, Analytics) need to react when physical inventory transitions occur or clinical compliance decisions are rendered. Direct method calls from producers to consumers would create tight coupling and violate bounded context isolation.

## Decision
Introduce an event-driven architecture powered by an in-process `EventBus` (`events/bus.py`). Producers (`InventoryManager`, `ClinicalDecisionManager`) publish immutable events (`InventoryEvent`, `ComplianceDecision`) to channel topics, while consumers (`AlertManager`, `HardwareController`, `Dashboard`) subscribe to channels without coupling.

## Consequences
- **Positive**: Complete decoupling between event producers and consumers.
- **Positive**: Subscribing new consumers (e.g. Analytics, Push Notifications) requires zero modifications to producers.
- **Negative**: In-process bus requires careful exception handling in subscriber callbacks.
