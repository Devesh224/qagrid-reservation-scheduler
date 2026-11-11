from datetime import datetime, timedelta, timezone
import uuid
import pytest
from pydantic import ValidationError
from app.schemas import ReservationCreate

def payload(start, end):
    return {
        "environment_id": uuid.uuid4(),
        "requester": "  qa@example.com  ",
        "purpose": "  regression  ",
        "start_time": start,
        "end_time": end,
    }

def test_valid_future_period_and_trimmed_fields():
    start = datetime.now(timezone.utc) + timedelta(days=1)
    item = ReservationCreate(**payload(start, start + timedelta(hours=1)))
    assert item.requester == "qa@example.com"
    assert item.purpose == "regression"

@pytest.mark.parametrize("offset", [timedelta(hours=-1), timedelta(0)])
def test_end_must_follow_start(offset):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(ValidationError):
        ReservationCreate(**payload(start, start + offset))

def test_timezone_is_required():
    start = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    with pytest.raises(ValidationError):
        ReservationCreate(**payload(start, start + timedelta(hours=1)))
