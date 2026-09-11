# Technical Design & Architecture Report: Alert Engine Subsystem v0.1.0
**Project**: AI-Powered Medicine Dispensing System  
**Doc ID**: `docs/05_ALERT_ENGINE.md`  
**Status**: Architecture & Design Phase (Phase 1 In Progress)  
**Date**: July 2026  

---

## Executive Summary

The **Alert Engine Subsystem** (`alerting/`) is a pure delivery consumer responsible for dispatching real-time notifications, caregiver SMS alerts, push notifications, and local audio/visual alarms when non-compliant or critical clinical decisions occur.

Operating downstream of the **Clinical Decision Engine**, it consumes immutable `ComplianceDecision` payloads. Strictly obeying **ADR-008 (Clinical Decision Boundary Isolation)**, the Alert Engine evaluates **zero medical or clinical rules**, acting solely as a message mapping and dispatching router.

---

## 1. Objectives & Delivery Principles

1. **Zero Medical Rule Logic**: Consumes `ComplianceDecision` payloads without re-evaluating medical rules.
2. **Channel Mapping**: Maps decision outcomes (`DOSE_MISSED`, `WRONG_MEDICINE`, `EXPIRED_MEDICINE`, `EXTRA_DOSE`) to alert channels (LOG, PUSH_NOTIFICATION, SMS, ALARM_BUZZER).
3. **Pluggable Dispatchers**: Abstract `AbstractAlertDispatcher` interface supporting `MockAlertDispatcher`, `TerminalAlertDispatcher`, and future SMS/Push integrations.
4. **EventBus Integration**: Subscribes to the in-process `EventBus` on the `"compliance_decision"` topic.

---

## 2. Package Topology (`alerting/`)

```text
alerting/
├── __init__.py          # Package exports & versioning (0.1.0)
├── enums.py             # AlertChannel, AlertSeverity
├── exceptions.py        # AlertEngineError hierarchy
├── models.py            # AlertMessage dataclass
├── dispatchers.py       # AbstractAlertDispatcher, MockAlertDispatcher, TerminalAlertDispatcher
└── manager.py           # AlertManager facade & EventBus subscriber
```

---

## 3. Phased Development Roadmap & Verification Status

```text
✓ Phase 1: Domain Contracts & Dispatcher Interfaces (enums.py, models.py, dispatchers.py) [COMPLETED]
✓ Phase 2: AlertManager Facade & EventBus Integration (alerting/manager.py) [COMPLETED]
✓ Phase 3: Unit & System Integration Tests (tests/test_alerting.py) [COMPLETED - 3/3 Tests Passed]
```

---

## 4. Architectural Quality Attributes

1. **Zero Rule Leakage**: Strict adherence to ADR-008. Does not perform medical evaluation.
2. **Decoupled Subscription**: Subscribes to `EventBus` topic `"compliance_decision"`.
3. **Pluggable Dispatchers**: Supports terminal logs, audio buzzers, SMS, and push notification targets.

---

## Appendix: System Verification Log Output

```text
Ran 117 tests in 6.005s

OK (114 Platform Core + 3 Alert Engine Tests Passed)
```

