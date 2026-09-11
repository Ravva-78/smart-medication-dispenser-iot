"""
Alert Engine Subsystem High-Level Orchestrator Facade & EventBus Subscriber.

Purpose:
    Acts as the entry point and subscriber for consuming ComplianceDecision events
    and mapping them to AlertMessage notifications without evaluating clinical rules.

Responsibilities:
    - Map `ComplianceDecision.outcome` to `AlertMessage` severity and channels.
    - Dispatch alerts through registered `AbstractAlertDispatcher` implementations.
    - Subscribe to `EventBus` topic `"compliance_decision"`.

Dependencies:
    - Standard library `uuid`, `logging`, `typing`.
    - `core.ids.IDGenerator`.
    - `clinical.models.ComplianceDecision`.
    - `clinical.enums.DecisionOutcome`.
    - `alerting.enums.AlertChannel`, `alerting.enums.AlertSeverity`.
    - `alerting.models.AlertMessage`.
    - `alerting.dispatchers.AbstractAlertDispatcher`, `alerting.dispatchers.MockAlertDispatcher`.
    - `events.bus.EventBus`, `events.bus.EventSubscriber`.
"""

import logging
from typing import List, Optional
from core.ids import IDGenerator
from clinical.models import ComplianceDecision
from clinical.enums import DecisionOutcome
from alerting.enums import AlertChannel, AlertSeverity
from alerting.models import AlertMessage
from alerting.dispatchers import AbstractAlertDispatcher, MockAlertDispatcher
from events.bus import EventBus, EventSubscriber

logger = logging.getLogger(__name__)


class AlertManager(EventSubscriber):
    """Alert Engine facade orchestrator mapping decisions to notifications."""

    def __init__(
        self,
        dispatchers: Optional[List[AbstractAlertDispatcher]] = None,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize AlertManager facade.

        Args:
            dispatchers: List of alert dispatcher instances (defaults to MockAlertDispatcher).
            event_bus: Optional EventBus instance for subscribing to compliance_decision channel.
        """
        self.dispatchers = dispatchers if dispatchers is not None else [MockAlertDispatcher()]
        self.event_bus = event_bus if event_bus is not None else EventBus.get_instance()
        self._history: List[AlertMessage] = []

        # Subscribe to EventBus topic
        self.event_bus.subscribe("compliance_decision", self)

    def on_event(self, event_type: str, payload: object) -> None:
        """EventBus callback handling published compliance decisions."""
        if isinstance(payload, ComplianceDecision):
            self.process_decision(payload)

    def process_decision(self, decision: ComplianceDecision) -> List[AlertMessage]:
        """
        Map a ComplianceDecision to AlertMessage instances and dispatch across channels.

        Args:
            decision: ComplianceDecision instance.

        Returns:
            List of generated and dispatched AlertMessage payloads.
        """
        messages: List[AlertMessage] = []

        if decision.outcome == DecisionOutcome.CORRECT_DOSE:
            msg = AlertMessage(
                alert_id=IDGenerator.generate("alt", 8),
                timestamp=decision.timestamp,
                patient_id=decision.patient_id,
                decision_id=decision.decision_id,
                severity=AlertSeverity.INFO,
                channel=AlertChannel.LOG,
                title="Dose Verified",
                message=decision.reason,
                recipient="System Audit Log & Caregiver Records",
            )
            messages.append(msg)

        elif decision.outcome == DecisionOutcome.WRONG_MEDICINE:
            m1 = AlertMessage(
                alert_id=IDGenerator.generate("alt", 8),
                timestamp=decision.timestamp,
                patient_id=decision.patient_id,
                decision_id=decision.decision_id,
                severity=AlertSeverity.CRITICAL,
                channel=AlertChannel.ALARM_BUZZER,
                title="CRITICAL: Wrong Medicine Removed",
                message=decision.reason,
                recipient=f"IoT Dispenser Device Buzzer (Patient {decision.patient_id})",
            )
            m2 = AlertMessage(
                alert_id=IDGenerator.generate("alt", 8),
                timestamp=decision.timestamp,
                patient_id=decision.patient_id,
                decision_id=decision.decision_id,
                severity=AlertSeverity.CRITICAL,
                channel=AlertChannel.CAREGIVER_ALERT,
                title="EMERGENCY: Patient Wrong Medicine Alert",
                message=decision.reason,
                recipient=f"Assigned Caregiver of Patient {decision.patient_id}",
            )
            messages.extend([m1, m2])

        elif decision.outcome == DecisionOutcome.EXPIRED_MEDICINE:
            msg = AlertMessage(
                alert_id=IDGenerator.generate("alt", 8),
                timestamp=decision.timestamp,
                patient_id=decision.patient_id,
                decision_id=decision.decision_id,
                severity=AlertSeverity.CRITICAL,
                channel=AlertChannel.CAREGIVER_ALERT,
                title="WARNING: Expired Medicine Removed",
                message=decision.reason,
                recipient=f"Assigned Caregiver of Patient {decision.patient_id}",
            )
            messages.append(msg)

        elif decision.outcome in (DecisionOutcome.DOSE_MISSED, DecisionOutcome.EXTRA_DOSE):
            msg = AlertMessage(
                alert_id=IDGenerator.generate("alt", 8),
                timestamp=decision.timestamp,
                patient_id=decision.patient_id,
                decision_id=decision.decision_id,
                severity=AlertSeverity.WARNING,
                channel=AlertChannel.PUSH_NOTIFICATION,
                title=f"Compliance Notice: {decision.outcome.value}",
                message=decision.reason,
                recipient=f"Assigned Caregiver of Patient {decision.patient_id}",
            )
            messages.append(msg)

        # Dispatch messages across registered dispatchers
        for msg in messages:
            self._history.append(msg)
            for dispatcher in self.dispatchers:
                try:
                    dispatcher.dispatch(msg)
                except Exception as err:
                    logger.error("Dispatcher %s failed: %s", dispatcher.get_dispatcher_name(), err)

        return messages

    def get_alert_history(self, patient_id: Optional[str] = None) -> List[AlertMessage]:
        """Retrieve dispatched alert history."""
        if patient_id is not None:
            return [a for a in self._history if a.patient_id == patient_id]
        return list(self._history)


__all__ = ["AlertManager"]
