import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    name: str
    event_date: date | None = None
    expires_at: datetime


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    host_id: uuid.UUID
    name: str
    event_date: date | None
    expires_at: datetime
    status: str
    created_at: datetime
