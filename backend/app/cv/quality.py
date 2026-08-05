"""Face-crop quality gates.

is_face_usable() gates individual detections in an already-uploaded event
photo. It's deliberately permissive — the guest can't retake someone else's
photo, so we only reject faces genuinely too poor to embed and match.

validate_selfie() gates the guest's onboarding selfie. It's deliberately
stricter — the guest can retake it immediately, so we ask for a single,
well-lit, reasonably large face and tell them exactly why a bad shot failed.
"""

from dataclasses import dataclass

import cv2
import numpy as np
import structlog

from app.config import settings
from app.cv.detector import detect_faces
from app.cv.imaging import crop_face

log = structlog.get_logger()


@dataclass
class QualityResult:
    ok: bool
    reason: str | None = None


def _shorter_side(bbox: np.ndarray) -> float:
    x1, y1, x2, y2 = bbox
    return float(min(x2 - x1, y2 - y1))


def _blur_variance(crop: np.ndarray) -> float:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def is_face_usable(image: np.ndarray, bbox: np.ndarray, det_score: float) -> QualityResult:
    if _shorter_side(bbox) < settings.face_min_size_px:
        result = QualityResult(False, "face_too_small")
    elif det_score < settings.face_det_score_min:
        result = QualityResult(False, "low_det_confidence")
    else:
        crop = crop_face(image, bbox)
        if crop.size == 0:
            result = QualityResult(False, "invalid_crop")
        elif _blur_variance(crop) < settings.face_blur_variance_min:
            result = QualityResult(False, "too_blurry")
        else:
            result = QualityResult(True)

    log.debug("cv.quality.face_checked", ok=result.ok, reason=result.reason, det_score=det_score)
    return result


def validate_selfie(image: np.ndarray) -> QualityResult:
    detections = detect_faces(image)

    if len(detections) == 0:
        result = QualityResult(False, "no_face_detected")
    elif len(detections) > 1:
        result = QualityResult(False, "multiple_faces_detected")
    else:
        face = detections[0]
        if _shorter_side(face.bbox) < settings.selfie_min_face_size_px:
            result = QualityResult(False, "face_too_small")
        else:
            crop = crop_face(image, face.bbox)
            if crop.size == 0:
                result = QualityResult(False, "invalid_crop")
            else:
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
                brightness = float(gray.mean())
                if brightness < settings.selfie_brightness_min:
                    result = QualityResult(False, "too_dark")
                elif brightness > settings.selfie_brightness_max:
                    result = QualityResult(False, "too_bright")
                else:
                    result = QualityResult(True)

    log.info("cv.quality.selfie_validated", ok=result.ok, reason=result.reason, face_count=len(detections))
    return result
