"""
Phase 3: Baseline Inspection (10/10 Tablets Present).

Tests:
  - InventoryManager.from_inspection() with 10/10 present
  - InventoryValidator passes all 9 mathematical checks
  - InventoryComparator emits EventType.CREATED
  - InventoryState status = NORMAL
  - InventoryHistory records the first snapshot

Run:
  python -m qa_testing.phase3_baseline_inspection
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.inspection_result import InspectionResult, PocketResult
from inventory.manager import InventoryManager
from inventory.enums import InventoryStatus, EventType
from inventory.validator import InventoryValidator
from inventory.formatter import InventoryFormatter


def run_baseline_inspection():
    """Simulate a vision pipeline output with 10/10 tablets present."""

    print("\n--- Step 1: Constructing Fake Vision Pipeline Output (10/10 Present) ---")
    pockets = [
        PocketResult(index=i, class_name="present", confidence=0.97, bbox=(i*10, 0, i*10+50, 50))
        for i in range(1, 11)
    ]
    inspection = InspectionResult(
        total=10,
        present=10,
        missing=0,
        avg_confidence=0.97,
        pockets=pockets,
    )
    print(f"  InspectionResult: total={inspection.total}, present={inspection.present}, missing={inspection.missing}")
    print(f"  Pockets created: {len(inspection.pockets)}")
    print(f"  Missing indices: {inspection.missing_indices}")

    print("\n--- Step 2: Feeding into InventoryManager.from_inspection() ---")
    inv_mgr = InventoryManager()
    strip_id = "strip_TEST_E2E_baseline"

    state, event = inv_mgr.from_inspection(
        result=inspection,
        strip_id=strip_id,
        image_name="baseline_test.jpg",
        camera_id="CAM-TEST",
        inspection_time=datetime.now(timezone.utc),
    )

    print(f"  Strip ID: {state.strip_id}")
    print(f"  Status: {state.status.value}")
    print(f"  Total Slots: {state.total_slots}")
    print(f"  Present: {state.present_count}")
    print(f"  Missing: {state.missing_count}")
    print(f"  Missing Slots: {state.missing_slots}")
    print(f"  Occupancy: {state.occupancy_percentage}%")
    print(f"  Avg Confidence: {state.average_confidence}")

    print(f"\n  Event ID: {event.event_id}")
    print(f"  Event Type: {event.event_type.value}")
    print(f"  Delta Present: {event.delta_present}")
    print(f"  Delta Missing: {event.delta_missing}")
    print(f"  Removed Slots: {event.removed_slots}")
    print(f"  Is Material Change: {event.is_material_change}")

    # --- VERIFICATION CHECKS ---
    print("\n--- Step 3: Verification Checks ---")
    checks = {}

    # Check 1: Event type is CREATED (first inspection for this strip)
    checks["Event type == CREATED"] = event.event_type == EventType.CREATED

    # Check 2: State status is NORMAL (all pills present, high confidence)
    checks["State status == NORMAL"] = state.status == InventoryStatus.NORMAL

    # Check 3: Counts are correct
    checks["present_count == 10"] = state.present_count == 10
    checks["missing_count == 0"] = state.missing_count == 0
    checks["total_slots == 10"] = state.total_slots == 10

    # Check 4: Occupancy is 100%
    checks["Occupancy == 100.0%"] = state.occupancy_percentage == 100.0

    # Check 5: No missing slots
    checks["missing_slots == ()"] = state.missing_slots == ()

    # Check 6: Validator passes (all 9 math rules)
    try:
        InventoryValidator.validate(state)
        checks["InventoryValidator.validate() PASSED"] = True
    except Exception as err:
        checks["InventoryValidator.validate() PASSED"] = False
        print(f"    Validator Error: {err}")

    # Check 7: Delta present equals total (first creation)
    checks["delta_present == 10 (baseline)"] = event.delta_present == 10

    # Check 8: History recorded
    history = inv_mgr._get_or_create_history(strip_id)
    checks["History has 1 snapshot"] = len(history.get_snapshots()) == 1
    checks["History latest state matches"] = history.get_latest_state() == state

    all_passed = True
    for check_name, passed in checks.items():
        icon = "[+]" if passed else "[-]"
        status = "PASS" if passed else "FAIL"
        print(f"  {icon} {check_name}: {status}")
        if not passed:
            all_passed = False

    # Print formatted summary
    print("\n--- Formatted Inventory Summary ---")
    print(InventoryFormatter.to_terminal_summary(state))
    print()
    print(InventoryFormatter.format_event_terminal(event))

    print()
    if all_passed:
        print("=" * 55)
        print("  PHASE 3: BASELINE INSPECTION -> ALL CHECKS PASSED")
        print("=" * 55)
    else:
        print("=" * 55)
        print("  PHASE 3: SOME CHECKS FAILED")
        print("=" * 55)
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 55)
    print("  PHASE 3: BASELINE INSPECTION (10/10 PRESENT)")
    print("=" * 55)
    run_baseline_inspection()
