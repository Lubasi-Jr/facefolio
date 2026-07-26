"""Image derivatives and face cropping.

Derivatives are built directly from a source file path and returned as bytes
for the caller to upload — this module never talks to app/storage/, per the
app/cv/ layering rule.
"""

import time
from io import BytesIO
from pathlib import Path

import numpy as np
import structlog
from PIL import Image, ImageOps

log = structlog.get_logger()

# Hardcoded rather than Settings fields: these are encoding/pipeline choices,
# not deployment config that varies between environments.
WEB_LONG_EDGE_PX = 1600
WEB_QUALITY = 80

THUMB_LONG_EDGE_PX = 400
THUMB_QUALITY = 80


def _load_rgb(source_path: str | Path) -> Image.Image:
    image = Image.open(source_path)
    # Bake EXIF orientation into the pixels before we strip EXIF on save —
    # otherwise photos taken in portrait would come out sideways.
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def _resize_to_webp_bytes(image: Image.Image, long_edge_px: int, quality: int) -> bytes:
    resized = image.copy()
    # Preserves aspect ratio, fits within (long_edge_px, long_edge_px).
    resized.thumbnail((long_edge_px, long_edge_px), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    # No exif= kwarg passed, so Pillow writes no EXIF block into the output.
    resized.save(buffer, format="WEBP", quality=quality)
    return buffer.getvalue()


def build_web_derivative(source_path: str | Path) -> bytes:
    log.debug("cv.imaging.web_derivative.started", source_path=str(source_path))
    start = time.monotonic()

    image = _load_rgb(source_path)
    data = _resize_to_webp_bytes(image, WEB_LONG_EDGE_PX, WEB_QUALITY)

    duration_ms = int((time.monotonic() - start) * 1000)
    log.debug("cv.imaging.web_derivative.completed", bytes=len(data), duration_ms=duration_ms)
    return data


def build_thumbnail(source_path: str | Path) -> bytes:
    log.debug("cv.imaging.thumbnail.started", source_path=str(source_path))
    start = time.monotonic()

    image = _load_rgb(source_path)
    data = _resize_to_webp_bytes(image, THUMB_LONG_EDGE_PX, THUMB_QUALITY)

    duration_ms = int((time.monotonic() - start) * 1000)
    log.debug("cv.imaging.thumbnail.completed", bytes=len(data), duration_ms=duration_ms)
    return data


def crop_face(image: np.ndarray, bbox: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = bbox.astype(int)
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, width), min(y2, height)
    return image[y1:y2, x1:x2]
