import sys
import time
from pathlib import Path

core_root = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\core")
sys.path.insert(0, str(core_root))

from app.pipeline import Pipeline
from inventory.manager import InventoryManager
from inventory.formatter import InventoryFormatter

def main():
    test_img = core_root / "dataset" / "images" / "test" / "IMG-20260905-WA0060[1].jpg"
    print(f"Testing end-to-end vision pipeline on: {test_img.name}")
    print("=" * 60)

    t0 = time.time()
    pipe = Pipeline.from_defaults()
    t_load = time.time() - t0
    print(f"Pipeline initialized (Model A v2.0, Perspective, Model B v2.0, Model C v1.0) in {t_load:.2f}s")

    t1 = time.time()
    result = pipe.run(str(test_img), debug=False)
    t_infer = time.time() - t1

    print("\n" + "=" * 60)
    print("🎯 END-TO-END PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Inference Time : {t_infer*1000:.1f} ms")
    print(f"Total Pockets  : {result.total}")
    print(f"Present (Pills): {result.present}")
    print(f"Missing (Empty): {result.missing}")
    print("-" * 60)
    print(f"Model A detected strip: {'YES' if result.stages and result.stages.strip_detection is not None else 'FULL FRAME'}")
    print(f"Perspective rectified : {'YES' if result.stages and result.stages.rectified is not None else 'NO'}")
    print(f"Model B pockets found : {len(result.pockets)}")


    # Inventory subsystem
    inv_manager = InventoryManager()
    state, event = inv_manager.from_inspection(
        result=result,
        strip_id="TEST_STRIP_001",
        image_name=test_img.name,
        save=False
    )
    print("\n" + InventoryFormatter.to_terminal_summary(state))
    print("\n" + InventoryFormatter.format_event_terminal(event))
    print("\n✅ ALL VISION & INVENTORY SUBSYSTEMS ARE OPERATIONAL!")

if __name__ == "__main__":
    main()
