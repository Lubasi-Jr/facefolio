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
    matched_count: int
    matched_photo_ids: list[uuid.UUID]
