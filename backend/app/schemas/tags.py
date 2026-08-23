import uuid
from typing import Literal

from pydantic import BaseModel


class PendingTag(BaseModel):
    photo_id: uuid.UUID
    similarity: float
    # The face crop if one was stored, otherwise the photo's thumbnail —
    # either way, something the guest can look at to say yes/no.
    crop_url: str


class PendingTagsResponse(BaseModel):
    tags: list[PendingTag]


class TagReviewResponse(BaseModel):
    photo_id: uuid.UUID
    status: Literal["confirmed", "rejected"]
    source: str
