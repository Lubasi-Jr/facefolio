import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class InvitationCreate(BaseModel):
    # Only used to invite guests; a host's invitation row is created
    # automatically alongside the event, not through this schema.
    email: EmailStr | None = None


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    invite_token: str
    email: EmailStr | None
    user_id: uuid.UUID | None
    role: Literal["host", "guest"]
    status: Literal["pending", "joined", "revoked"]
    created_at: datetime


class InvitationLinkRead(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    status: Literal["pending", "joined", "revoked"]
    invite_link: str


class InvitationPublicRead(BaseModel):
    # Unauthenticated, pre-membership view for the /join/:token page — no host
    # email, photo keys, or other event internals. event_id IS included: the
    # guest flow needs it for the event-scoped enroll calls after joining,
    # and it carries no more information than the invite link itself already
    # implies.
    event_id: uuid.UUID
    event_name: str
    # Derived from Invitation.status + Event.status; expired takes precedence
    # over revoked when both apply.
    join_status: Literal["joinable", "revoked", "expired"]
