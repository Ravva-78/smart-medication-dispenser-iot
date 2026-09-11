"""
End-to-end blister strip inspection pipeline.

Orchestrates: Model A -> Perspective -> Model B -> Extractor -> Model C -> Counter
"""
from pathlib import Path
import cv2
import numpy as np

from config import (
    MODEL_A_PATH, MODEL_B_PATH, MODEL_C_PATH,
    CONF_MODEL_A, CONF_MODEL_B,
    SAVE_STAGE_IMAGES, DEBUG_DIR,
    PERSPECTIVE_ENABLED, PERSPECTIVE_WIDTH, PERSPECTIVE_HEIGHT,
)
from pipeline.inspection_result import InspectionResult, PocketResult, StageImages


def _as_numpy_boxes(boxes_xyxy):
    cpu = getattr(boxes_xyxy, "cpu", None)
    if callable(cpu):
        boxes_xyxy = cpu()

    numpy_fn = getattr(boxes_xyxy, "numpy", None)
    if callable(numpy_fn):
        return numpy_fn()

    return np.asarray(boxes_xyxy)


class Pipeline:
    def __init__(self, strip_detector=None, perspective_fn=None,
                 pocket_detector=None, classifier=None,
                 conf_a=None, conf_b=None):
        """
        Args:
            strip_detector: callable(image) -> list of strip crops
            perspective_fn: callable(crop) -> rectified image
            pocket_detector: callable(image) -> list of (x1,y1,x2,y2) boxes
            classifier: callable(list_of_crops) -> list of (class, confidence)
        """
        self.strip_detector = strip_detector
        self.perspective_fn = perspective_fn
        self.pocket_detector = pocket_detector
        self.classifier = classifier
        self.conf_a = conf_a
        self.conf_b = conf_b

    @classmethod
    def from_defaults(cls, conf_a=None, conf_b=None):
        """Build pipeline with default model implementations."""
        import sys
        ROOT = Path(__file__).parent.parent
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT / "models" / "model_c"))

        from ultralytics import YOLO
        try:
            from models.model_c.predict import load_model as load_c, predict_batch
        except ImportError:
            sys.path.insert(0, str(ROOT / "models" / "model_c"))
            from predict import load_model as load_c, predict_batch
        from pipeline.perspective import correct_perspective


        strip_detector = None
        pocket_detector = None
        classifier = None

        if MODEL_A_PATH.exists():
            model_a = YOLO(str(MODEL_A_PATH))
            def _strip_detector(img, conf=None):
                c = conf if conf is not None else CONF_MODEL_A
                results = list(model_a(img, conf=c, iou=0.35, verbose=False))
                crops = []
                for r in results:
                    if hasattr(r, "boxes") and r.boxes is not None:
                        for box in _as_numpy_boxes(r.boxes.xyxy):
                            x1, y1, x2, y2 = map(int, box)
                            crop = img[y1:y2, x1:x2]
                            if crop.size > 0:
                                crops.append(crop)
                return crops if crops else [img]
            strip_detector = _strip_detector

        if MODEL_B_PATH.exists():
            model_b = YOLO(str(MODEL_B_PATH))
            def _pocket_detector(img, conf=None):
                c = conf if conf is not None else CONF_MODEL_B
                results = list(model_b(img, conf=c, iou=0.35, verbose=False))
                if results and hasattr(results[0], "boxes") and results[0].boxes is not None and len(results[0].boxes) > 0:
                    return _as_numpy_boxes(results[0].boxes.xyxy)
                return []
            pocket_detector = _pocket_detector


        if MODEL_C_PATH.exists():
            load_c()
            def _classifier(crops):
                return predict_batch(crops)
            classifier = _classifier

        def _perspective(img):
            return correct_perspective(img, PERSPECTIVE_WIDTH, PERSPECTIVE_HEIGHT)

        return cls(
            strip_detector=strip_detector,
            perspective_fn=_perspective if PERSPECTIVE_ENABLED else None,
            pocket_detector=pocket_detector,
            classifier=classifier,
            conf_a=conf_a,
            conf_b=conf_b,
        )

    def run(self, image, debug=False, conf_a=None, conf_b=None):
        """
        Run the full pipeline with stage execution reporting.

        Args:
            image: BGR numpy array or image path
            debug: if True, save stage images to DEBUG_DIR
            conf_a: optional Model A confidence override
            conf_b: optional Model B confidence override

        Returns:
            InspectionResult
        """
        report = []

        if isinstance(image, (str, Path)):
            img = cv2.imread(str(image))
            if img is not None:
                report.append(f"✓ Input Image Loaded: {Path(image).name} ({img.shape[1]}x{img.shape[0]} px)")
            else:
                img = np.zeros((100, 100, 3), dtype=np.uint8)
                report.append(f"✗ Failed to load image: {Path(image).name}")
        else:
            img = image.copy()
            report.append(f"✓ Input Image Loaded: NumPy Array ({img.shape[1]}x{img.shape[0]} px)")

        stages = StageImages(input=img)
        images_to_save = SAVE_STAGE_IMAGES or debug
        model_a_conf = conf_a if conf_a is not None else self.conf_a
        model_b_conf = conf_b if conf_b is not None else self.conf_b

        # Stage 1: Model A - Detect strip
        if self.strip_detector:
            strip_crops = self.strip_detector(img, conf=model_a_conf)
            report.append(f"✓ Stage 1 (Model A Strip Detector): {len(strip_crops)} strip region(s) found")
        else:
            strip_crops = [img]
            report.append("ℹ Stage 1 (Model A): Defaulting to full image")

        all_pocket_results = []
        stage_pocket_crops = []

        for strip_idx, strip_img in enumerate(strip_crops):
            # Stage 2: Perspective correction
            if self.perspective_fn:
                rectified = self.perspective_fn(strip_img)
                report.append(f"✓ Stage 2 (Perspective Rectification): Success ({rectified.shape[1]}x{rectified.shape[0]} px)")
            else:
                rectified = strip_img
                report.append("ℹ Stage 2 (Perspective): Skipped")

            stages.rectified = rectified

            if images_to_save:
                _save_debug(DEBUG_DIR / f"stage1_strip_{strip_idx}.jpg", strip_img)
                _save_debug(DEBUG_DIR / f"stage2_rectified_{strip_idx}.jpg", rectified)

            # Stage 3: Model B - Detect pockets
            if self.pocket_detector:
                pockets = self.pocket_detector(rectified, conf=model_b_conf)
                report.append(f"✓ Stage 3 (Model B Pocket Detector): {len(pockets)} pocket(s) detected")
            else:
                pockets = []
                report.append("⚠ Stage 3 (Model B): Detector not loaded")

            stages.pocket_detection = pockets

            if len(pockets) == 0:
                report.append("✗ Stage 3 (Model B): 0 pockets detected. Pipeline stopped further processing.")
                continue

            # Stage 4: Pocket Extractor (in RAM, no disk)
            try:
                from models.model_c.scripts.pocket_extractor import extract_pockets
            except ImportError:
                sys.path.insert(0, str(ROOT / "models" / "model_c" / "scripts"))
                from pocket_extractor import extract_pockets
            crops_data = extract_pockets(rectified, pockets, save=False)
            crop_images = [c for _, c, _ in crops_data]
            stage_pocket_crops.extend(crop_images)
            stages.pocket_crops = crop_images
            report.append(f"✓ Stage 4 (Pocket Extractor): {len(crop_images)} pocket crop(s) extracted")

            if images_to_save:
                for ci, (name, crop, _) in enumerate(crops_data):
                    _save_debug(DEBUG_DIR / f"stage4_{name}", crop)

            # Stage 5: Model C - Classify each pocket
            if self.classifier and crop_images:
                results = self.classifier(crop_images)
                all_pocket_results.extend(zip(results, crops_data))
                report.append(f"✓ Stage 5 (Model C Tablet Classifier): {len(results)} pocket(s) classified")

        stages.pocket_crops = stage_pocket_crops

        # Stage 6: Counter
        try:
            from models.model_c.counter import count
        except ImportError:
            sys.path.insert(0, str(ROOT / "models" / "model_c"))
            from counter import count
        raw_counts = count([(cls, conf) for (cls, conf), _ in all_pocket_results])


        result = InspectionResult(
            total=raw_counts["total"],
            present=raw_counts["present"],
            missing=raw_counts["missing"],
            stages=stages,
            execution_report=report,
        )


        # Build per-pocket results
        for i, ((cls, conf), (_, _, bbox)) in enumerate(all_pocket_results):
            result.pockets.append(PocketResult(
                index=i + 1,
                class_name=cls,
                confidence=conf,
                bbox=tuple(map(int, bbox)),
            ))

        confs = [p.confidence for p in result.pockets]
        result.avg_confidence = float(np.mean(confs)) if confs else 0.0

        return result


def _save_debug(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path> [--debug]")
        sys.exit(1)

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

        # Top status banner
        banner = f"Total: {result.total} | Present: {result.present} | Missing: {result.missing}"
        cv2.putText(vis, banner, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        window_name = f"End-to-End Pipeline Inspection - {Path(sys.argv[1]).name}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, vis)
        print("\nPress any key to close the inspection window...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
