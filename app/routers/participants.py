from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.participant import Participant
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantResponse,
    ParticipantUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_participant(
    participant_data: ParticipantCreate,
    db: DbSession,
):
    existing_participant = (
        db.query(Participant)
        .filter(Participant.email == participant_data.email)
        .first()
    )

    if existing_participant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Participant with this email already exists",
        )

    participant = Participant(
        full_name=participant_data.full_name,
        email=participant_data.email,
        phone=participant_data.phone,
        organization=participant_data.organization,
    )

    db.add(participant)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Participant with this email already exists",
        )

    db.refresh(participant)

    return participant


@router.get(
    "/",
    response_model=list[ParticipantResponse],
)
def get_participants(
    db: DbSession,
):
    return db.query(Participant).all()


@router.get(
    "/{participant_id}",
    response_model=ParticipantResponse,
)
def get_participant(
    participant_id: int,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    return participant


@router.put(
    "/{participant_id}",
    response_model=ParticipantResponse,
)
def update_participant(
    participant_id: int,
    participant_data: ParticipantUpdate,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    update_data = participant_data.model_dump(
        exclude_unset=True
    )

    if "email" in update_data:
        existing_participant = (
            db.query(Participant)
            .filter(
                Participant.email == update_data["email"],
                Participant.id != participant_id,
            )
            .first()
        )

        if existing_participant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Participant with this email already exists",
            )

    for field, value in update_data.items():
        setattr(participant, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Participant with this email already exists",
        )

    db.refresh(participant)

    return participant


@router.delete(
    "/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_participant(
    participant_id: int,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    db.delete(participant)
    db.commit()

  