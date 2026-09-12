from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hotel_request import HotelRequest
from app.models.participant import Participant
from app.schemas.hotel_request import (
    HotelRequestCreate,
    HotelRequestResponse,
    HotelRequestUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=HotelRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hotel_request(
    request_data: HotelRequestCreate,
    db: DbSession,
):
    participant = (
        db.query(Participant)
        .filter(Participant.id == request_data.participant_id)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )

    hotel_request = HotelRequest(
        participant_id=request_data.participant_id,
        required=request_data.required,
        check_in=request_data.check_in,
        check_out=request_data.check_out,
    )

    db.add(hotel_request)
    db.commit()
    db.refresh(hotel_request)

    return hotel_request


@router.get(
    "/",
    response_model=list[HotelRequestResponse],
)
def get_hotel_requests(
    db: DbSession,
):
    return db.query(HotelRequest).all()


@router.get(
    "/{request_id}",
    response_model=HotelRequestResponse,
)
def get_hotel_request(
    request_id: int,
    db: DbSession,
):
    hotel_request = (
        db.query(HotelRequest)
        .filter(HotelRequest.id == request_id)
        .first()
    )

    if not hotel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel request not found",
        )

    return hotel_request


@router.put(
    "/{request_id}",
    response_model=HotelRequestResponse,
)
def update_hotel_request(
    request_id: int,
    request_data: HotelRequestUpdate,
    db: DbSession,
):
    hotel_request = (
        db.query(HotelRequest)
        .filter(HotelRequest.id == request_id)
        .first()
    )

    if not hotel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel request not found",
        )

    hotel_request.required = request_data.required
    hotel_request.check_in = request_data.check_in
    hotel_request.check_out = request_data.check_out

    db.commit()
    db.refresh(hotel_request)

    return hotel_request


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_hotel_request(
    request_id: int,
    db: DbSession,
):
    hotel_request = (
        db.query(HotelRequest)
        .filter(HotelRequest.id == request_id)
        .first()
    )

    if not hotel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel request not found",
        )

    db.delete(hotel_request)
    db.commit()