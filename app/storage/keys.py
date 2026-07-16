"""Deterministic storage key builders for Supabase Storage.

Keys are derived from ids, never from uploaded filenames. This is what makes
Celery tasks idempotent under at-least-once delivery: reprocessing a photo
always overwrites the same key instead of writing a new, orphaned one.
"""

import uuid


def original_key(event_id: uuid.UUID, photo_id: uuid.UUID) -> str:
    return f"events/{event_id}/originals/{photo_id}.jpg"


def web_key(event_id: uuid.UUID, photo_id: uuid.UUID) -> str:
    return f"events/{event_id}/web/{photo_id}.jpg"


def thumb_key(event_id: uuid.UUID, photo_id: uuid.UUID) -> str:
    return f"events/{event_id}/thumbs/{photo_id}.jpg"


def face_crop_key(event_id: uuid.UUID, photo_id: uuid.UUID, face_id: uuid.UUID) -> str:
    return f"events/{event_id}/faces/{photo_id}/{face_id}.jpg"


def enrollment_selfie_key(event_id: uuid.UUID, user_id: uuid.UUID) -> str:
    return f"events/{event_id}/enrollments/{user_id}.jpg"
