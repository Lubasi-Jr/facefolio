import uuid
from typing import Literal

from pydantic import BaseModel, Field


class PreparePhotoItem(BaseModel):
    filename: str
    size_bytes: int = Field(gt=0)


class PreparePhotosRequest(BaseModel):
    photos: list[PreparePhotoItem]


class PreparedPhotoUpload(BaseModel):
    photo_id: uuid.UUID
    upload_url: str


class PreparePhotosResponse(BaseModel):
    photos: list[PreparedPhotoUpload]


class PhotoConfirmResponse(BaseModel):
    photo_id: uuid.UUID
    status: Literal["queued"]


class ProcessingStatusResponse(BaseModel):
    awaiting_upload: int = 0
    queued: int = 0
    processing: int = 0
    processed: int = 0
    failed: int = 0


class GalleryPhoto(BaseModel):
    photo_id: uuid.UUID
    web_url: str
    thumb_url: str


class GalleryResponse(BaseModel):
    photos: list[GalleryPhoto]
