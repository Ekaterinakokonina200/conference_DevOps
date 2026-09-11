from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.application import Application
from app.models.participant import Participant
from app.models.payment import Payment
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]





@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    application_data: ApplicationCreate,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == application_data.participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    application = Application(
        participant_id=application_data.participant_id,
        status="pending",
    )

    db.add(application)
    db.commit()
    db.refresh(application)


    return application







@router.get(
    "/",
    response_model=list[ApplicationResponse],
)
def get_applications(
    db: DbSession,
):
    return db.query(Application).all()





@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
)
def get_application(
    application_id: int,
    db: DbSession,
):
    application = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application





@router.put(
    "/{application_id}",
    response_model=ApplicationResponse,
)
def update_application(
    application_id: int,
    application_data: ApplicationUpdate,
    db: DbSession,
):
    application = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    if application_data.status == "confirmed":
        payment = (
            db.query(Payment)
            .filter(
                Payment.participant_id == application.participant_id,
                Payment.status == "paid",
            )
            .first()
        )

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration fee must be paid before confirmation",
            )

    application.status = application_data.status

    db.commit()
    db.refresh(application)

    return application



@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_application(
    application_id: int,
    db: DbSession,
):
    application = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    db.delete(application)
    db.commit()