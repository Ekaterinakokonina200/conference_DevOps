from pydantic import BaseModel, ConfigDict, EmailStr


class ParticipantCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    organization: str | None = None


class ParticipantUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    organization: str | None = None


class ParticipantResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    organization: str | None

    model_config = ConfigDict(from_attributes=True)