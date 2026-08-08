"""Loads the InsightFace model once per process and caches it.

Model loading (reading ONNX weights, building the onnxruntime session) is slow
enough that it must not happen per-task. get_model() is the only entry point;
it lazily initializes the model on first call and returns the cached instance
on every call after that.
"""

import threading
import time

import structlog
from insightface.app import FaceAnalysis

log = structlog.get_logger()

# Hardcoded rather than a Settings field: this is a code-level implementation
# choice (which bundle/providers the pipeline uses), not deployment config
# that varies between environments.
MODEL_NAME = "buffalo_l"
PROVIDERS = ["CPUExecutionProvider"]
DET_SIZE = (640, 640)

_model: FaceAnalysis | None = None
_lock = threading.Lock()


def get_model() -> FaceAnalysis:
    global _model

    if _model is not None:
        return _model

    with _lock:
        # Re-check: another thread may have finished loading while we waited.
        if _model is not None:
            return _model

        log.info("cv.model.loading", model_name=MODEL_NAME, providers=PROVIDERS)
        start = time.monotonic()

        model = FaceAnalysis(name=MODEL_NAME, providers=PROVIDERS)
        # ctx_id selects the GPU device and is ignored when only
        # CPUExecutionProvider is configured; 0 is the conventional value.
        model.prepare(ctx_id=0, det_size=DET_SIZE)

        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("cv.model.loaded", model_name=MODEL_NAME, duration_ms=duration_ms)

        _model = model

    return _model
