from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invitation import Invitation
from app.models.participant import Participant
from app.schemas.invitation import (
    InvitationCreate,
    InvitationResponse,
    InvitationUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    invitation_data: InvitationCreate,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == invitation_data.participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    invitation = Invitation(
        participant_id=invitation_data.participant_id,
        status="created",
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return invitation


@router.get(
    "/",
    response_model=list[InvitationResponse],
)
def get_invitations(
    db: DbSession,
):
    return db.query(Invitation).all()


@router.get(
    "/{invitation_id}",
    response_model=InvitationResponse,
)
def get_invitation(
    invitation_id: int,
    db: DbSession,
):
    invitation = (
        db.query(Invitation)
        .filter(Invitation.id == invitation_id)
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    return invitation


@router.put(
    "/{invitation_id}",
    response_model=InvitationResponse,
)
def update_invitation(
    invitation_id: int,
    invitation_data: InvitationUpdate,
    db: DbSession,
):
    invitation = (
        db.query(Invitation)
        .filter(Invitation.id == invitation_id)
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    invitation.status = invitation_data.status

    if invitation_data.status == "sent":
        invitation.sent_at = datetime.now(UTC)

    db.commit()
    db.refresh(invitation)

    return invitation


@router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_invitation(
    invitation_id: int,
    db: DbSession,
):
    invitation = (
        db.query(Invitation)
        .filter(Invitation.id == invitation_id)
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    db.delete(invitation)
    db.commit()