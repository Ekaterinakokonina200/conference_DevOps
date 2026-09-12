from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.participant import Participant
from app.models.thesis import Thesis
from app.schemas.thesis import (
    ThesisCreate,
    ThesisResponse,
    ThesisUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=ThesisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_thesis(
    thesis_data: ThesisCreate,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == thesis_data.participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    thesis = Thesis(
        participant_id=thesis_data.participant_id,
        title=thesis_data.title,
        file_url=thesis_data.file_url,
        status="submitted",
    )

    db.add(thesis)
    db.commit()
    db.refresh(thesis)

    return thesis


@router.get(
    "/",
    response_model=list[ThesisResponse],
)
def get_theses(
    db: DbSession,
):
    return db.query(Thesis).all()


@router.get(
    "/{thesis_id}",
    response_model=ThesisResponse,
)
def get_thesis(
    thesis_id: int,
    db: DbSession,
):
    thesis = (
        db.query(Thesis)
        .filter(Thesis.id == thesis_id)
        .first()
    )

    if not thesis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thesis not found",
        )

    return thesis


@router.put(
    "/{thesis_id}",
    response_model=ThesisResponse,
)
def update_thesis(
    thesis_id: int,
    thesis_data: ThesisUpdate,
    db: DbSession,
):
    thesis = (
        db.query(Thesis)
        .filter(Thesis.id == thesis_id)
        .first()
    )

    if not thesis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thesis not found",
        )

    thesis.status = thesis_data.status

    db.commit()
    db.refresh(thesis)

    return thesis


@router.delete(
    "/{thesis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_thesis(
    thesis_id: int,
    db: DbSession,
):
    thesis = (
        db.query(Thesis)
        .filter(Thesis.id == thesis_id)
        .first()
    )

    if not thesis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thesis not found",
        )

    db.delete(thesis)
    db.commit()