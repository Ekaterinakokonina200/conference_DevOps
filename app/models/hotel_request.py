from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer

from app.database import Base


class HotelRequest(Base):
    __tablename__ = "hotel_requests"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    participant_id = Column(
        Integer,
        ForeignKey("participants.id"),
        nullable=False,
    )

    required = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    check_in = Column(
        Date,
        nullable=True,
    )

    check_out = Column(
        Date,
        nullable=True,
    )