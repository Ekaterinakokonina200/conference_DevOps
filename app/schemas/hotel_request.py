from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class HotelRequestCreate(BaseModel):
    participant_id: int
    required: bool
    check_in: date | None = None
    check_out: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.required:
            if self.check_in is None or self.check_out is None:
                raise ValueError(
                    "Check-in and check-out dates are required"
                )

            if self.check_out <= self.check_in:
                raise ValueError(
                    "Check-out date must be after check-in date"
                )

        return self


class HotelRequestUpdate(BaseModel):
    required: bool
    check_in: date | None = None
    check_out: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.required:
            if self.check_in is None or self.check_out is None:
                raise ValueError(
                    "Check-in and check-out dates are required"
                )

            if self.check_out <= self.check_in:
                raise ValueError(
                    "Check-out date must be after check-in date"
                )

        return self


class HotelRequestResponse(BaseModel):
    id: int
    participant_id: int
    required: bool
    check_in: date | None
    check_out: date | None

    model_config = ConfigDict(from_attributes=True)