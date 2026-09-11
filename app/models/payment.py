from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    participant_id = Column(
        Integer,
        ForeignKey("participants.id"),
        nullable=False,
    )

    amount = Column(
        Float,
        nullable=False,
    )

    status = Column(
        String(50),
        nullable=False,
        default="pending",
    )

    payment_date = Column(
        DateTime,
        nullable=True,
    )