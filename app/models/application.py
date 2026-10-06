from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'rejected')",
            name="ck_applications_status",
        ),
        CheckConstraint(
            "status <> 'rejected' OR rejection_reason IS NOT NULL",
            name="ck_applications_rejection_reason",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    participant_id = Column(
        Integer,
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(50),
        nullable=False,
        default="pending",
    )

    rejection_reason = Column(
        String(500),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
