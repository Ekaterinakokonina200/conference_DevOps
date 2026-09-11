from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class Invitation(Base):
    __tablename__ = "invitations"

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

    status = Column(
        String(50),
        nullable=False,
        default="created",
    )

    sent_at = Column(
        DateTime,
        nullable=True,
    )