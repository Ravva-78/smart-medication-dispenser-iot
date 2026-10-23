"""
Background warm-up so the first real scan is not slow.

Without it, the first request that needs the service loads Models A/B/C (about 9 s) and the first inference
adds CUDA start-up (up to 2 s) plus EasyOCR initialisation (about 4 s). `start` does that work in a daemon thread
at backend start-up; routes that use the models call `wait()` so a request never touches a model while it is
still being loaded. Disable with WARMUP_ON_START=0. It runs only dummy (blank) frames: no patient data, no database.
"""
import logging
import threading
import time

import numpy as np

logger = logging.getLogger(__name__)
_idle = threading.Event()
_idle.set()  # set = nothing is warming up


def wait(timeout=90):
    """Block while a warm-up is in progress (returns immediately when none is)."""
    _idle.wait(timeout)


def run(get_service):
    t0 = time.perf_counter()
    try:
        controller = get_service().inspection_controller        # loads Models A/B/C when first built
        t_models = time.perf_counter() - t0
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        pipe = controller.pipe
        if pipe is not None:
            for stage in (pipe.strip_detector, pipe.pocket_detector):
                if stage:
                    stage(frame)
            if pipe.classifier:
                pipe.classifier([frame[:224, :224]])
        t_infer = time.perf_counter() - t0 - t_models
        backend = getattr(controller.ocr_mgr, "backend", None)
        if backend is not None and hasattr(backend, "_get_reader"):
            backend._get_reader()
            backend.extract_text(frame)
        logger.info("warm-up done: models %.1fs, first inference %.1fs, OCR %.1fs",
                    t_models, t_infer, time.perf_counter() - t0 - t_models - t_infer)
    except Exception as err:  # warm-up is an optimisation; a failure must never stop the backend
        logger.warning("warm-up failed (%s); the first scan will be slower", type(err).__name__)
    finally:
        _idle.set()


def start(get_service):
    _idle.clear()
    threading.Thread(target=run, args=(get_service,), name="warmup", daemon=True).start()
