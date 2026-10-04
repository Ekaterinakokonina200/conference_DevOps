from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'cancelled')",
            name="ck_payments_status",
        ),
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)

    participant_id = Column(
        Integer,
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
