"""Calcule de disponibilitate: program, mentenanță și capacitate, pe sloturi de 30 de minute."""
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import MaintenanceWindow, OperatingSchedule, Reservation, ReservationStatus, Resource, ResourceStatus

SLOT = timedelta(minutes=30)
ACTIVE_STATUSES = (ReservationStatus.PENDING, ReservationStatus.AWAITING_TRAINING, ReservationStatus.APPROVED)
LOCAL_ZONE = ZoneInfo(settings.timezone)


def is_aligned(moment: datetime) -> bool:
    return int(moment.timestamp()) % int(SLOT.total_seconds()) == 0


def iter_slots(start: datetime, end: datetime) -> Iterator[datetime]:
    current = start
    while current < end:
        yield current
        current += SLOT


def within_schedule(db: Session, resource_id: int, start: datetime, end: datetime) -> bool:
    local_start, local_end = start.astimezone(LOCAL_ZONE), end.astimezone(LOCAL_ZONE)
    if local_start.date() != local_end.date():
        return False
    return (
        db.scalar(
            select(OperatingSchedule.id).where(
                OperatingSchedule.resource_id == resource_id,
                OperatingSchedule.zi_saptamana == local_start.isoweekday(),
                OperatingSchedule.ora_deschidere <= local_start.time(),
                OperatingSchedule.ora_inchidere >= local_end.time(),
            )
        )
        is not None
    )


def overlapping_maintenance(db: Session, resource_id: int, start: datetime, end: datetime) -> MaintenanceWindow | None:
    return db.scalar(
        select(MaintenanceWindow).where(
            MaintenanceWindow.resource_id == resource_id,
            MaintenanceWindow.anulata_la.is_(None),
            MaintenanceWindow.data_inceput < end,
            MaintenanceWindow.data_sfarsit > start,
        )
    )


def _active_reservations(db: Session, resource_id: int, start: datetime, end: datetime) -> list[Reservation]:
    return list(
        db.scalars(
            select(Reservation).where(
                Reservation.resource_id == resource_id,
                Reservation.status.in_(ACTIVE_STATUSES),
                Reservation.data_inceput < end,
                Reservation.data_sfarsit > start,
            )
        )
    )


def has_free_place(db: Session, resource: Resource, start: datetime, end: datetime) -> bool:
    reservations = _active_reservations(db, resource.id, start, end)
    return all(
        sum(r.data_inceput < slot + SLOT and r.data_sfarsit > slot for r in reservations) < resource.max_echipe_simultane
        for slot in iter_slots(start, end)
    )


def current_availability(db: Session, resource: Resource, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    slot_end = now + timedelta(seconds=1)
    occupied = db.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(
            Reservation.resource_id == resource.id,
            Reservation.status.in_(ACTIVE_STATUSES),
            Reservation.data_inceput < slot_end,
            Reservation.data_sfarsit > now,
        )
    )
    if (
        resource.status is not ResourceStatus.ACTIVE
        or occupied >= resource.max_echipe_simultane
        or overlapping_maintenance(db, resource.id, now, slot_end)
    ):
        return "REZERVATA"
    return "LIBERA"


def slots_between(db: Session, resource: Resource, first_day: date, last_day: date) -> list[dict]:
    range_start = datetime.combine(first_day, datetime.min.time(), LOCAL_ZONE)
    range_end = datetime.combine(last_day + timedelta(days=1), datetime.min.time(), LOCAL_ZONE)
    reservations = _active_reservations(db, resource.id, range_start, range_end)
    windows = db.scalars(
        select(MaintenanceWindow).where(
            MaintenanceWindow.resource_id == resource.id,
            MaintenanceWindow.anulata_la.is_(None),
            MaintenanceWindow.data_inceput < range_end,
            MaintenanceWindow.data_sfarsit > range_start,
        )
    ).all()
    schedules = db.scalars(
        select(OperatingSchedule)
        .where(OperatingSchedule.resource_id == resource.id)
        .order_by(OperatingSchedule.zi_saptamana, OperatingSchedule.ora_deschidere)
    ).all()

    slots = []
    day = first_day
    while day <= last_day:
        for schedule in schedules:
            if schedule.zi_saptamana != day.isoweekday():
                continue
            opening = datetime.combine(day, schedule.ora_deschidere, LOCAL_ZONE).astimezone(timezone.utc)
            closing = datetime.combine(day, schedule.ora_inchidere, LOCAL_ZONE).astimezone(timezone.utc)
            for start in iter_slots(opening, closing):
                end = start + SLOT
                taken = sum(r.data_inceput < end and r.data_sfarsit > start for r in reservations)
                if any(w.data_inceput < end and w.data_sfarsit > start for w in windows):
                    status = "MENTENANTA"
                elif taken >= resource.max_echipe_simultane:
                    status = "OCUPAT"
                else:
                    status = "PARTIAL" if taken else "LIBER"
                slots.append(
                    {
                        "start": start,
                        "end": end,
                        "status": status,
                        "locuri_ocupate": taken,
                        "locuri_totale": resource.max_echipe_simultane,
                    }
                )
        day += timedelta(days=1)
    return slots
