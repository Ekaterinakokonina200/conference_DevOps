from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

InvitationStatus = Literal[
    "created",
    "sent",
    "accepted",
    "declined",
]


class InvitationCreate(BaseModel):
    participant_id: int


class InvitationUpdate(BaseModel):
    status: InvitationStatus


class InvitationResponse(BaseModel):
    id: int
    participant_id: int
    status: str
    sent_at: datetime | None

    model_config = ConfigDict(from_attributes=True)