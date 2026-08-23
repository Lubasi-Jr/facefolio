import uuid

from pydantic import BaseModel


class PrepareEnrollmentResponse(BaseModel):
    selfie_key: str
    upload_url: str


class EnrollRequest(BaseModel):
    # Selfie is uploaded to storage via a presigned URL first, same pattern
    # as photos — this only carries the resulting key and consent.
    selfie_key: str
    consent: bool


class EnrollResponse(BaseModel):
    # Confirmed matches only — this is the immediate "Photos of you" result.
    matched_count: int
    matched_photo_ids: list[uuid.UUID]
    # Matches banded 'pending_guest' (see app/db/queries/tags.classify_match):
    # stored as tags already, but need the guest to confirm before they count
    # as "yours". Not included in matched_count/matched_photo_ids above.
    pending_review_count: int
