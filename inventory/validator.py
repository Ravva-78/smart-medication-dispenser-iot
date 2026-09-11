"""
Inventory Subsystem Technical & Mathematical Validator.

Purpose:
    Validates physical, mathematical, and structural consistency of InventoryState objects.

Responsibilities:
    - Enforce `total_slots > 0` (blister strip must contain physical slots).
    - Verify non-negative pocket counts.
    - Assert `present_count + missing_count == total_slots`.
    - Validate confidence bounds `[0.0, 1.0]`.
    - Check missing slot indices for uniqueness, ascending sort order, and valid range `[1, total_slots]`.
    - Recompute and verify derived `occupancy_percentage`.
    - Log error details before raising descriptive `ValidationError`.

Dependencies:
    - `inventory.models.InventoryState`
    - `inventory.exceptions.ValidationError`
"""

import logging
from inventory.models import InventoryState
from inventory.exceptions import ValidationError

logger = logging.getLogger(__name__)

OCCUPANCY_TOLERANCE = 0.01


class InventoryValidator:
    """Validator class providing technical and mathematical correctness checks for InventoryState."""

    @staticmethod
    def validate(state: InventoryState) -> bool:
        """
        Validate an InventoryState object for mathematical and structural correctness.

        Args:
            state: InventoryState instance to validate.

        Returns:
            True if state passes all validation rules.

        Raises:
            ValidationError: If any mathematical, structural, or range contract is violated.
        """
        logger.debug("Validating InventoryState for strip: %s", state.strip_id)

        # 1. Total slots strictly positive check
        if state.total_slots <= 0:
            logger.error("Invalid total_slots for strip %s: %d", state.strip_id, state.total_slots)
            raise ValidationError(f"total_slots must be strictly positive (> 0): got {state.total_slots}")

        # 2. Non-negative counts check
        if state.present_count < 0 or state.missing_count < 0:
            logger.error(
                "Negative count for strip %s: present=%d, missing=%d",
                state.strip_id, state.present_count, state.missing_count
            )
            raise ValidationError(
                f"Counts cannot be negative: present={state.present_count}, missing={state.missing_count}"
            )

        # 3. Count sum equality check
        if state.present_count + state.missing_count != state.total_slots:
            logger.error(
                "Count sum mismatch for strip %s: present(%d) + missing(%d) != total(%d)",
                state.strip_id, state.present_count, state.missing_count, state.total_slots
            )
            raise ValidationError(
                f"Count sum mismatch: present_count ({state.present_count}) + "
                f"missing_count ({state.missing_count}) = {state.present_count + state.missing_count} "
                f"must equal total_slots ({state.total_slots})"
            )

        # 4. Confidence bounds check
        if not (0.0 <= state.average_confidence <= 1.0):
            logger.error(
                "Invalid average_confidence for strip %s: %.4f",
                state.strip_id, state.average_confidence
            )
            raise ValidationError(
                f"average_confidence ({state.average_confidence}) must be between 0.0 and 1.0"
            )

        # 5. Missing slots count check
        if len(state.missing_slots) != state.missing_count:
            logger.error(
                "Missing slots count mismatch for strip %s: len=%d, count=%d",
                state.strip_id, len(state.missing_slots), state.missing_count
            )
            raise ValidationError(
                f"missing_slots length ({len(state.missing_slots)}) does not match "
                f"missing_count ({state.missing_count})"
            )

        # 6. Duplicate missing slots check
        if len(state.missing_slots) != len(set(state.missing_slots)):
            logger.error("Duplicate indices in missing_slots for strip %s: %s", state.strip_id, state.missing_slots)
            raise ValidationError(
                f"Duplicate indices found in missing_slots: {state.missing_slots}"
            )

        # 7. Sorted missing slots check
        if state.missing_slots != tuple(sorted(state.missing_slots)):
            logger.error("Unsorted missing_slots for strip %s: %s", state.strip_id, state.missing_slots)
            raise ValidationError(
                f"missing_slots tuple must be sorted in ascending order: got {state.missing_slots}"
            )

        # 8. Missing slots index bounds check
        for slot_idx in state.missing_slots:
            if slot_idx < 1 or slot_idx > state.total_slots:
                logger.error("Missing slot index out of range for strip %s: %d", state.strip_id, slot_idx)
                raise ValidationError(
                    f"Missing slot index {slot_idx} is out of range [1, {state.total_slots}]"
                )

        # 9. Derived occupancy percentage recomputation check
        expected_occupancy = round((state.present_count / state.total_slots * 100), 2)
        if abs(state.occupancy_percentage - expected_occupancy) > OCCUPANCY_TOLERANCE:
            logger.error(
                "Occupancy mismatch for strip %s: stored=%.2f%%, recomputed=%.2f%%",
                state.strip_id, state.occupancy_percentage, expected_occupancy
            )
            raise ValidationError(
                f"Occupancy percentage mismatch: stored={state.occupancy_percentage}%, "
                f"recomputed={expected_occupancy}%"
            )

        logger.debug("InventoryState validation passed for strip: %s", state.strip_id)
        return True


__all__ = ["InventoryValidator", "OCCUPANCY_TOLERANCE"]
