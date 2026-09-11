"""
Clinical Decision Engine Safety & Compliance Rules Evaluator.

Purpose:
    Evaluates safety, drug matching, expiry verification, and schedule compliance rules.

Responsibilities:
    - Compare OCR verified `MedicineIdentity` against `Prescription` requirements.
    - Check expiry dates against current timestamp.
    - Evaluate `InventoryEvent` state changes against `DoseSchedule` time windows.
    - Classify final `DecisionOutcome` (`CORRECT_DOSE`, `DOSE_MISSED`, `WRONG_MEDICINE`, `EXTRA_DOSE`, `EXPIRED_MEDICINE`).

Dependencies:
    - Standard library `datetime`, `logging`, `typing`.
    - `inventory.events.InventoryEvent`, `inventory.enums.EventType`.
    - `ocr.models.MedicineIdentity`.
    - `clinical.models.Prescription`, `clinical.models.DoseSchedule`.
    - `clinical.enums.DecisionOutcome`, `clinical.enums.ScheduleWindowStatus`.
    - `clinical.schedule.DoseScheduler`.
"""

import logging
from datetime import datetime, timezone
from typing import Tuple, Optional

from inventory.events import InventoryEvent
from inventory.enums import EventType
from ocr.models import MedicineIdentity
from clinical.models import Prescription, DoseSchedule
from clinical.enums import DecisionOutcome, ScheduleWindowStatus
from clinical.schedule import DoseScheduler

logger = logging.getLogger(__name__)


class ClinicalRulesEngine:
    """Clinical safety and compliance rules evaluator."""

    @staticmethod
    def evaluate_medicine_match(
        identity: Optional[MedicineIdentity],
        prescription: Prescription,
    ) -> Tuple[bool, str]:
        """Verify extracted medicine identity against prescription requirements."""
        if identity is None or not identity.medicine_name or identity.medicine_name == "Unknown Medicine" or identity.confidence < 0.30:
            return True, "No definitive OCR identity extracted; skipping drug name match rule"

        if identity.medicine_name.strip().lower() != prescription.medicine_name.strip().lower():
            return False, f"Medicine mismatch: extracted '{identity.medicine_name}' != prescribed '{prescription.medicine_name}'"

        if prescription.strength and identity.strength:
            norm_id_str = identity.strength.strip().lower().replace(" ", "")
            norm_rx_str = prescription.strength.strip().lower().replace(" ", "")
            if norm_id_str != norm_rx_str:
                return False, f"Strength mismatch: extracted '{identity.strength}' != prescribed '{prescription.strength}'"

        return True, "Medicine and strength match prescription"

    @staticmethod
    def evaluate_expiry_safety(
        identity: Optional[MedicineIdentity],
        current_time: datetime,
    ) -> Tuple[bool, str]:
        """Verify that medicine batch expiry date is not past current execution timestamp."""
        if identity is None or not identity.expiry_date:
            return True, "No expiry date provided; skipping expiry safety rule"

        try:
            exp_date = datetime.fromisoformat(identity.expiry_date)
            # Ensure timezone awareness for comparison
            if exp_date.tzinfo is None:
                exp_date = exp_date.replace(tzinfo=timezone.utc)
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)

            if current_time > exp_date:
                return False, f"Expired medicine: batch expired on {identity.expiry_date}"
        except Exception as err:
            logger.warning("Failed to parse expiry date string '%s': %s", identity.expiry_date, err)

        return True, "Medicine is within valid shelf life"

    @classmethod
    def evaluate_compliance(
        cls,
        event: InventoryEvent,
        identity: Optional[MedicineIdentity],
        prescription: Prescription,
        schedule: Optional[DoseSchedule] = None,
    ) -> Tuple[DecisionOutcome, str, bool]:
        """
        Evaluate full clinical rules engine pipeline.

        Args:
            event: InventoryEvent transition object.
            identity: Optional OCR verified MedicineIdentity.
            prescription: Patient Prescription specification.
            schedule: Optional DoseSchedule time window specification.

        Returns:
            Tuple of (DecisionOutcome, reason_string, actionable_flag).
        """
        eval_time = event.timestamp

        # 1. Medicine Matching Rule Check (evaluated first if OCR identity provided)
        match_ok, match_reason = cls.evaluate_medicine_match(identity, prescription)
        if not match_ok:
            return DecisionOutcome.WRONG_MEDICINE, match_reason, True

        # 2. Expiry Safety Rule Check (evaluated second if expiry provided)
        expiry_ok, expiry_reason = cls.evaluate_expiry_safety(identity, eval_time)
        if not expiry_ok:
            return DecisionOutcome.EXPIRED_MEDICINE, expiry_reason, True

        # 3. Non-material event check (if no tablet removed and drug matches)
        if event.delta_present == 0 or (not event.is_material_change and event.event_type != EventType.TABLET_REMOVED):
            # If this is the initial baseline setup (Scan #1), always return PENDING (baseline established)
            if event.event_type == EventType.CREATED or event.previous_state is None:
                return DecisionOutcome.PENDING, "Initial baseline inventory state recorded", False

            # Timing rule for Scan #2: if count is unchanged 5+ minutes AFTER scheduled dose time -> Medicine not taken
            if schedule is not None and schedule.scheduled_time is not None:
                eval_utc = eval_time.astimezone(timezone.utc) if eval_time.tzinfo else eval_time
                sched_utc = schedule.scheduled_time.astimezone(timezone.utc) if schedule.scheduled_time.tzinfo else schedule.scheduled_time
                diff_mins = (eval_utc - sched_utc).total_seconds() / 60.0
                if diff_mins >= 5.0:
                    return (
                        DecisionOutcome.DOSE_MISSED,
                        f"Medicine not taken: Scheduled dose at {sched_utc.strftime('%H:%M')} elapsed by >5 minutes with 0 tablets removed",
                        True,
                    )
            return DecisionOutcome.PENDING, "No physical inventory state transition", False


        # 4. Multi-tablet removal check (Two or more removed / Extra Dose / Overdose safety rule)
        num_removed = abs(event.delta_present) if event.delta_present < 0 else 0
        if num_removed > 1:
            return (
                DecisionOutcome.EXTRA_DOSE,
                f"Two or more removed (Overdose): {num_removed} tablets removed simultaneously (prescribed 1)",
                True,
            )


        # 5. Schedule Window Evaluation Rule Check
        if schedule is not None:
            window_status = DoseScheduler.evaluate_window(schedule, eval_time)
            if window_status == ScheduleWindowStatus.EARLY:
                # If taken more than 5 minutes before scheduled dose time
                return DecisionOutcome.EXTRA_DOSE, "Tablet removed too early (more than 5 minutes before scheduled dose window)", True
            if window_status == ScheduleWindowStatus.LATE:
                return (
                    DecisionOutcome.CORRECT_DOSE,
                    f"Correct dose taken late: 1 tablet of {prescription.medicine_name} ({prescription.strength})",
                    True,
                )
            if window_status == ScheduleWindowStatus.MISSED:
                return (
                    DecisionOutcome.CORRECT_DOSE,
                    f"Correct dose taken after missed window: 1 tablet of {prescription.medicine_name} ({prescription.strength})",
                    True,
                )

        # Default success: 1 tablet taken
        return (
            DecisionOutcome.CORRECT_DOSE,
            f"Correct dose taken: 1 tablet of {prescription.medicine_name} ({prescription.strength})",
            True,
        )



__all__ = ["ClinicalRulesEngine"]
