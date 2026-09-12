from typing import Literal

from pydantic import BaseModel, ConfigDict

ThesisStatus = Literal[
    "submitted",
    "approved",
    "rejected",
]


class ThesisCreate(BaseModel):
    participant_id: int
    title: str
    file_url: str | None = None


class ThesisUpdate(BaseModel):
    status: ThesisStatus


class ThesisResponse(BaseModel):
    id: int
    participant_id: int
    title: str
    file_url: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)