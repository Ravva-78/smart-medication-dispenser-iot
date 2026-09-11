"""
Clinical Decision Engine High-Level Orchestrator Facade.

Purpose:
    Acts as the primary public API entry point for evaluating clinical rules,
    logging compliance audit decisions, and retrieving patient adherence metrics.

Responsibilities:
    - Evaluate real-time `InventoryEvent` and `MedicineIdentity` payloads against `Prescription` requirements.
    - Construct frozen `ComplianceDecision` records.
    - Maintain audit history via `ClinicalHistory`.
    - Provide patient adherence statistics.

Dependencies:
    - Standard library `uuid`, `logging`, `typing`.
    - `inventory.events.InventoryEvent`.
    - `ocr.models.MedicineIdentity`.
    - `clinical.models.Prescription`, `clinical.models.DoseSchedule`, `clinical.models.ComplianceDecision`.
    - `clinical.enums.DecisionOutcome`.
    - `clinical.rules.ClinicalRulesEngine`.
    - `clinical.history.ClinicalHistory`.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional

from inventory.events import InventoryEvent
from ocr.models import MedicineIdentity
from clinical.models import Prescription, DoseSchedule, ComplianceDecision
from clinical.enums import DecisionOutcome
from clinical.rules import ClinicalRulesEngine
from clinical.history import ClinicalHistory

from events.bus import EventBus

logger = logging.getLogger(__name__)


class ClinicalDecisionManager:
    """Orchestrator facade managing clinical rule evaluations and decision audit logs."""

    def __init__(
        self,
        history: Optional[ClinicalHistory] = None,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize ClinicalDecisionManager facade.

        Args:
            history: Optional ClinicalHistory audit tracker instance.
            event_bus: Optional EventBus instance.
        """
        self.history = history if history is not None else ClinicalHistory()
        self.event_bus = event_bus if event_bus is not None else EventBus.get_instance()


    def evaluate_event(
        self,
        event: InventoryEvent,
        prescription: Prescription,
        identity: Optional[MedicineIdentity] = None,
        schedule: Optional[DoseSchedule] = None,
    ) -> ComplianceDecision:
        """
        Evaluate an InventoryEvent and optional OCR identity against a patient prescription and schedule.

        Args:
            event: InventoryEvent state transition payload.
            prescription: Patient Prescription specification.
            identity: Optional OCR verified MedicineIdentity.
            schedule: Optional DoseSchedule time window specification.

        Returns:
            Constructed ComplianceDecision audit record.
        """
        logger.debug("Evaluating clinical event for patient %s (strip=%s)", prescription.patient_id, event.strip_id)

        outcome, reason, actionable = ClinicalRulesEngine.evaluate_compliance(
            event=event,
            identity=identity,
            prescription=prescription,
            schedule=schedule,
        )

        decision_id = f"dec_{uuid.uuid4().hex[:10]}"

        decision = ComplianceDecision(
            decision_id=decision_id,
            timestamp=event.timestamp,
            patient_id=prescription.patient_id,
            strip_id=event.strip_id,
            prescription_id=prescription.prescription_id,
            outcome=outcome,
            reason=reason,
            actionable=actionable,
            schema_version="1.0",
        )

        # Log decision in history tracker
        self.history.add_decision(decision)

        # Publish decision to EventBus subscribers
        self.event_bus.publish("compliance_decision", decision)

        logger.info("Clinical evaluation decision %s: %s (%s)", decision_id, outcome.value, reason)

        return decision


    def get_patient_metrics(self, patient_id: str) -> Dict[str, Any]:
        """Retrieve patient adherence metrics statistics."""
        return self.history.get_metrics(patient_id)

    def get_decision_history(
        self,
        patient_id: Optional[str] = None,
        outcome: Optional[DecisionOutcome] = None,
        limit: Optional[int] = None,
    ) -> List[ComplianceDecision]:
        """Retrieve recorded decision history filtered by criteria."""
        return self.history.get_decisions(patient_id=patient_id, outcome=outcome, limit=limit)


__all__ = ["ClinicalDecisionManager"]
