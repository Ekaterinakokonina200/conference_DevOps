from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from app.services.rules import validate_stay_dates


class HotelRequestCreate(BaseModel):
    participant_id: int
    required: bool
    check_in: date | None = None
    check_out: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        validate_stay_dates(self.required, self.check_in, self.check_out)
        return self


class HotelRequestUpdate(BaseModel):
    required: bool
    check_in: date | None = None
    check_out: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        validate_stay_dates(self.required, self.check_in, self.check_out)
        return self


class HotelRequestResponse(BaseModel):
    id: int
    participant_id: int
    required: bool
    check_in: date | None
    check_out: date | None

    model_config = ConfigDict(from_attributes=True)
