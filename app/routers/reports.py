from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.application import Application
from app.models.hotel_request import HotelRequest
from app.models.participant import Participant
from app.models.payment import Payment
from app.models.thesis import Thesis

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/summary")
def get_summary(db: DbSession):
    participants = db.query(Participant).count()

    confirmed = (
        db.query(Application)
        .filter(Application.status == "confirmed")
        .count()
    )

    payments_received = (
        db.query(Payment)
        .filter(Payment.status == "paid")
        .count()
    )

    theses_submitted = db.query(Thesis).count()

    hotel_required = (
        db.query(HotelRequest)
        .filter(HotelRequest.required.is_(True))
        .count()
    )

    return {
        "participants": participants,
        "confirmed": confirmed,
        "payments_received": payments_received,
        "theses_submitted": theses_submitted,
        "hotel_required": hotel_required,
    }