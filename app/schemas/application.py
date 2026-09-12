from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ApplicationStatus = Literal[
    "pending",
    "confirmed",
    "rejected",
]


class ApplicationCreate(BaseModel):
    participant_id: int


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationResponse(BaseModel):
    id: int
    participant_id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)