from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String

from app.database import Base


class Thesis(Base):
    __tablename__ = "theses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected')",
            name="ck_theses_status",
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

    title = Column(
        String(255),
        nullable=False,
    )

    file_url = Column(
        String(500),
        nullable=True,
    )

    status = Column(
        String(50),
        nullable=False,
        default="submitted",
    )
