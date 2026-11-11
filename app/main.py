import uuid
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from .database import get_db
from .models import Reservation
from .registry_client import require_bookable_environment
from .schemas import (AvailabilityRead, ReservationCreate, ReservationList,
    ReservationRead, ReservationStatus, validate_period)

app = FastAPI(title="QAGrid Reservation Scheduler", version="1.0.0")

def find(reservation_id: uuid.UUID, db: Session) -> Reservation:
    item = db.get(Reservation, reservation_id)
    if item is None:
        raise HTTPException(404, "Reservation not found")
    return item

def has_overlap(db: Session, environment_id: uuid.UUID, start: datetime, end: datetime) -> bool:
    stmt = select(Reservation.reservation_id).where(
        Reservation.environment_id == environment_id,
        Reservation.status == "CONFIRMED",
        Reservation.start_time < end,
        Reservation.end_time > start,
    ).limit(1)
    return db.scalar(stmt) is not None

def check_period(start: datetime, end: datetime) -> None:
    try:
        validate_period(start, end)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1 FROM reservations LIMIT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Scheduler database unavailable") from exc
    return {"status": "ready"}

@app.post("/api/v1/reservations", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
def create(payload: ReservationCreate, db: Session = Depends(get_db)):
    require_bookable_environment(payload.environment_id)
    if has_overlap(db, payload.environment_id, payload.start_time, payload.end_time):
        raise HTTPException(409, "Time slot overlaps an existing reservation")
    item = Reservation(**payload.model_dump(mode="python"), status="CONFIRMED")
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23P01":
            raise HTTPException(409, "Time slot overlaps an existing reservation") from exc
        raise
    db.refresh(item)
    return item

@app.get("/api/v1/reservations", response_model=ReservationList)
def list_reservations(
    requester: str | None = None,
    environment_id: uuid.UUID | None = None,
    status_filter: ReservationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Reservation)
    if requester:
        stmt = stmt.where(Reservation.requester == requester)
    if environment_id:
        stmt = stmt.where(Reservation.environment_id == environment_id)
    if status_filter:
        stmt = stmt.where(Reservation.status == status_filter.value)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Reservation.start_time.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}

@app.get("/api/v1/reservations/availability", response_model=AvailabilityRead)
def availability(
    environment_id: uuid.UUID,
    start_time: datetime,
    end_time: datetime,
    db: Session = Depends(get_db),
):
    check_period(start_time, end_time)
    require_bookable_environment(environment_id)
    return {"environment_id": environment_id, "start_time": start_time,
            "end_time": end_time, "available": not has_overlap(db, environment_id, start_time, end_time)}

@app.get("/api/v1/reservations/{reservation_id}", response_model=ReservationRead)
def get_reservation(reservation_id: uuid.UUID, db: Session = Depends(get_db)):
    return find(reservation_id, db)

@app.patch("/api/v1/reservations/{reservation_id}/cancel", response_model=ReservationRead)
def cancel(reservation_id: uuid.UUID, db: Session = Depends(get_db)):
    item = find(reservation_id, db)
    if item.status == "COMPLETED":
        raise HTTPException(409, "Completed reservation cannot be cancelled")
    if item.status != "CANCELLED":
        item.status = "CANCELLED"
        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)
    return item

@app.patch("/api/v1/reservations/{reservation_id}/complete", response_model=ReservationRead)
def complete(reservation_id: uuid.UUID, db: Session = Depends(get_db)):
    item = find(reservation_id, db)
    if item.status == "CANCELLED":
        raise HTTPException(409, "Cancelled reservation cannot be completed")
    if item.end_time > datetime.now(timezone.utc):
        raise HTTPException(409, "Reservation has not ended")
    if item.status != "COMPLETED":
        item.status = "COMPLETED"
        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)
    return item
