import uuid

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
    invitation = await create_guest_invitation(session, event_id=event_id, email=body.email)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation already claimed or revoked",
        )

    if await get_membership(session, invitation.event_id, user_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already a member of this event",
        )

    return await claim_invitation(session, invitation, user_id)
