import uuid
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class ReservationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

def validate_period(start: datetime, end: datetime) -> None:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start_time must include a timezone")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("end_time must include a timezone")
    if start <= datetime.now(timezone.utc):
        raise ValueError("start_time must be in the future")
    if end <= start:
        raise ValueError("end_time must be after start_time")

class ReservationCreate(BaseModel):
    environment_id: uuid.UUID
    requester: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=1000)
    start_time: datetime
    end_time: datetime

    @field_validator("requester", "purpose")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def valid_times(self):
        validate_period(self.start_time, self.end_time)
        return self

class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reservation_id: uuid.UUID
    environment_id: uuid.UUID
    requester: str
    purpose: str
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime

class ReservationList(BaseModel):
    items: list[ReservationRead]
    total: int
    limit: int
    offset: int

class AvailabilityRead(BaseModel):
    environment_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    available: bool
