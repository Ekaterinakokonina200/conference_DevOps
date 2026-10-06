from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.rules import rejection_reason_for

ApplicationStatus = Literal[
    "pending",
    "confirmed",
    "rejected",
]


class ApplicationCreate(BaseModel):
    participant_id: int


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus
    rejection_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_rejection_reason(self):
        self.rejection_reason = rejection_reason_for(self.status, self.rejection_reason)
        return self


class ApplicationResponse(BaseModel):
    id: int
    participant_id: int
    status: str
    rejection_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
