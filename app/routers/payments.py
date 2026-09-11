from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.participant import Participant
from app.models.payment import Payment
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payment_data: PaymentCreate,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == payment_data.participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    payment = Payment(
        participant_id=payment_data.participant_id,
        amount=payment_data.amount,
        status=payment_data.status,
    )

    if payment_data.status == "paid":
        payment.payment_date = datetime.now(UTC)

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


@router.get(
    "/",
    response_model=list[PaymentResponse],
)
def get_payments(
    db: DbSession,
):
    return db.query(Payment).all()


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: int,
    db: DbSession,
):
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    return payment


@router.put(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    db: DbSession,
):
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    payment.status = payment_data.status

    if payment_data.status == "paid":
        payment.payment_date = datetime.now(UTC)

    if payment_data.status != "paid":
        payment.payment_date = None

    db.commit()
    db.refresh(payment)

    return payment