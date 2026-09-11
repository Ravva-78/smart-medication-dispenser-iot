"""
Clinical Decision Engine Audit History Log & Metrics.

Purpose:
    Maintains a chronological, searchable audit record of ComplianceDecision events
    and computes adherence statistics for patient dashboards.

Responsibilities:
    - Append and store `ComplianceDecision` instances.
    - Query decisions by patient_id, strip_id, or DecisionOutcome.
    - Compute patient adherence percentage ($\text{correct\_doses} / \text{total\_actionable\_doses} \times 100\%$).

Dependencies:
    - Standard library `logging`, `typing`.
    - `clinical.models.ComplianceDecision`.
    - `clinical.enums.DecisionOutcome`.
"""

import logging
from typing import List, Dict, Any, Optional
from clinical.models import ComplianceDecision
from clinical.enums import DecisionOutcome

logger = logging.getLogger(__name__)


class ClinicalHistory:
    """In-memory chronological audit log tracker and adherence metrics provider."""

    def __init__(self):
        self._decisions: List[ComplianceDecision] = []

    def add_decision(self, decision: ComplianceDecision) -> None:
        """Append a new ComplianceDecision to the audit history log."""
        if not (isinstance(decision, ComplianceDecision) or hasattr(decision, "decision_id")):
            raise ValueError("Input must be a valid ComplianceDecision instance.")
        self._decisions.append(decision)
        logger.debug("Logged ComplianceDecision %s (outcome=%s)", decision.decision_id, decision.outcome.value)

    def get_decisions(
        self,
        patient_id: Optional[str] = None,
        outcome: Optional[DecisionOutcome] = None,
        limit: Optional[int] = None,
    ) -> List[ComplianceDecision]:
        """
        Query recorded ComplianceDecision events filtered by criteria.

        Args:
            patient_id: Optional filter for patient ID.
            outcome: Optional filter for DecisionOutcome.
            limit: Maximum number of recent decisions to return.

        Returns:
            List of matching ComplianceDecision instances.
        """
        results = self._decisions
        if patient_id is not None:
            results = [d for d in results if d.patient_id == patient_id]
        if outcome is not None:
            results = [d for d in results if d.outcome == outcome]

        if limit is not None and limit > 0:
            results = results[-limit:]

        return list(results)

    def get_metrics(self, patient_id: str) -> Dict[str, Any]:
        """
        Compute adherence statistics metrics for a specific patient.

        Args:
            patient_id: Patient ID string.

        Returns:
            Dictionary containing total_decisions, correct_doses, missed_doses,
            wrong_medicines, expired_medicines, extra_doses, and adherence_percentage.
        """
        patient_decisions = [d for d in self._decisions if d.patient_id == patient_id and d.actionable]

        total = len(patient_decisions)
        correct = sum(1 for d in patient_decisions if d.outcome == DecisionOutcome.CORRECT_DOSE)
        missed = sum(1 for d in patient_decisions if d.outcome == DecisionOutcome.DOSE_MISSED)
        wrong = sum(1 for d in patient_decisions if d.outcome == DecisionOutcome.WRONG_MEDICINE)
        expired = sum(1 for d in patient_decisions if d.outcome == DecisionOutcome.EXPIRED_MEDICINE)
        extra = sum(1 for d in patient_decisions if d.outcome == DecisionOutcome.EXTRA_DOSE)

        adherence_pct = round((correct / total) * 100.0, 2) if total > 0 else 100.0

        return {
            "patient_id": patient_id,
            "total_decisions": total,
            "correct_doses": correct,
            "missed_doses": missed,
            "wrong_medicines": wrong,
            "expired_medicines": expired,
            "extra_doses": extra,
            "adherence_percentage": adherence_pct,
        }

    def clear(self) -> None:
        """Reset internal history log array (for testing purposes)."""
        self._decisions.clear()


__all__ = ["ClinicalHistory"]
