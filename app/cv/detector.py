"""Face detection: runs the InsightFace model on an image and returns plain data.

buffalo_l's app.get() already does detection + landmark + recognition in one
pass, so the embedding returned here comes straight from InsightFace and is
NOT L2-normalized — normalization is a separate, deliberate step owned by
whatever layer writes embeddings to the database.
"""

import time
from dataclasses import dataclass

import numpy as np
import structlog

from app.cv.loader import get_model

log = structlog.get_logger()


@dataclass
class FaceDetection:
    bbox: np.ndarray  # (4,) float32: x1, y1, x2, y2
    det_score: float
    keypoints: np.ndarray  # (5, 2) float32: eyes, nose, mouth corners
    embedding: np.ndarray  # (512,) float32, raw / not normalized


def detect_faces(image: np.ndarray) -> list[FaceDetection]:
    log.debug("cv.detect.started", image_shape=image.shape)
    start = time.monotonic()

    model = get_model()
    faces = model.get(image)

    detections = [
        FaceDetection(
            bbox=face.bbox,
            det_score=float(face.det_score),
            keypoints=face.kps,
            embedding=face.embedding,
        )
        for face in faces
    ]

    duration_ms = int((time.monotonic() - start) * 1000)
    log.debug("cv.detect.completed", face_count=len(detections), duration_ms=duration_ms)

    return detections
