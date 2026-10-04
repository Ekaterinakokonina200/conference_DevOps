from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'sent', 'accepted', 'declined')",
            name="ck_invitations_status",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    participant_id = Column(
        Integer,
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
