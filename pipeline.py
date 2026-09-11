import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from app.pipeline import Pipeline, _save_debug

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path> [--debug]")
        sys.exit(1)

    import cv2
    import numpy as np

    debug = "--debug" in sys.argv
    pipe = Pipeline.from_defaults()
    result = pipe.run(sys.argv[1], debug=debug)
    
    # Process through Inventory Subsystem (Single Source of Truth)
    from inventory.manager import InventoryManager
    from inventory.formatter import InventoryFormatter

    inv_manager = InventoryManager()
    state, event = inv_manager.from_inspection(
        result=result,
        strip_id=None,  # Auto-generate temporary strip identity
        image_name=Path(sys.argv[1]).name,
        save=True,      # Save JSON record for CLI execution
    )

    print("\n" + InventoryFormatter.to_terminal_summary(state))
    print("\n" + InventoryFormatter.format_event_terminal(event))

    # Build visual visualization for pop-up window
    annotated = None
    if result.stages is not None:
        annotated = result.stages.rectified if result.stages.rectified is not None else result.stages.input

    if annotated is not None and hasattr(annotated, "copy"):
        vis = annotated.copy()
        for p in result.pockets:
            x1, y1, x2, y2 = p.bbox
            color = (0, 255, 0) if p.class_name == "present" else (0, 0, 255)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            label = f"P{p.index}: {p.class_name}"
            cv2.putText(vis, label, (x1, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        banner = f"Total: {result.total} | Present: {result.present} | Missing: {result.missing}"
        cv2.putText(vis, banner, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        window_name = f"End-to-End Pipeline Inspection - {Path(sys.argv[1]).name}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, vis)
        print("\nPress any key to close the inspection window...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
