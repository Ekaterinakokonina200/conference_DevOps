from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PaymentStatus = Literal[
    "pending",
    "paid",
    "cancelled",
]


class PaymentCreate(BaseModel):
    participant_id: int
    amount: float = Field(gt=0)
    status: PaymentStatus = "pending"


class PaymentUpdate(BaseModel):
    status: PaymentStatus


class PaymentResponse(BaseModel):
    id: int
    participant_id: int
    amount: float
    status: str
    payment_date: datetime | None

    model_config = ConfigDict(from_attributes=True)