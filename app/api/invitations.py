import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.guards import require_host
from app.config import settings
from app.db.queries.invitations import (
    claim_invitation,
    create_guest_invitation,
    get_invitation_by_token,
    get_membership,
)
from app.dependencies import CurrentUser, SessionDep
from app.schemas.invitations import InvitationCreate, InvitationLinkRead, InvitationRead

log = structlog.get_logger()

router = APIRouter(tags=["invitations"])


@router.post(
    "/events/{event_id}/invitations",
    response_model=InvitationLinkRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_host)],
)
async def create_invitation_endpoint(
    event_id: uuid.UUID,
    body: InvitationCreate,
    session: SessionDep,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id))
    invitation = await create_guest_invitation(session, event_id=event_id, email=body.email)
    log.info("invitation.created", invitation_id=str(invitation.id))
    return InvitationLinkRead(
        id=invitation.id,
        event_id=invitation.event_id,
        status=invitation.status,
        invite_link=f"{settings.frontend_origin}/join/{invitation.invite_token}",
    )


@router.post("/invitations/{token}/claim", response_model=InvitationRead)
async def claim_invitation_endpoint(
    token: str,
    session: SessionDep,
    user_id: CurrentUser,
):
    invitation = await get_invitation_by_token(session, token)
    if invitation is None:
        log.info("invitation.claim_rejected", reason="bad_token")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    structlog.contextvars.bind_contextvars(event_id=str(invitation.event_id))

    if invitation.status != "pending":
        log.info("invitation.claim_rejected", reason="not_pending")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation already claimed or revoked",
        )

    if await get_membership(session, invitation.event_id, user_id) is not None:
        log.info("invitation.claim_rejected", reason="already_member")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already a member of this event",
        )

    membership = await claim_invitation(session, invitation, user_id)
    log.info("invitation.claimed", invitation_id=str(membership.id))
    return membership
