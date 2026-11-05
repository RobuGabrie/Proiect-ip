from fastapi import APIRouter, BackgroundTasks
from fastapi import status as http_status

from app.dependencies import AdminUser, CurrentUser, DbSession, PageNumber, PageSize
from app.models import ReservationStatus
from app.schemas import RescheduleInput, ReservationInput, ReservationOut, ReservationPage
from app.services import notifications
from app.services import reservations as service

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get("", operation_id="listMyReservations", response_model=ReservationPage)
def list_my_reservations(
    user: CurrentUser,
    db: DbSession,
    status: ReservationStatus | None = None,
    q: str | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> ReservationPage:
    items, total = service.list_for_user(db, user, status, q, page, page_size)
    return ReservationPage(items=items, page=page, page_size=page_size, total=total)


@router.post("", operation_id="createReservation", response_model=ReservationOut, status_code=http_status.HTTP_201_CREATED)
def create_reservation(
    data: ReservationInput, user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> ReservationOut:
    reservation, created = service.create_reservation(db, user, data)
    notifications.schedule_delivery(background, db, created)
    return service.to_out(db, reservation)


@router.get("/{reservation_id}", operation_id="getReservation", response_model=ReservationOut)
def get_reservation(reservation_id: int, user: CurrentUser, db: DbSession) -> ReservationOut:
    return service.to_out(db, service.get_visible(db, user, reservation_id))


@router.post("/{reservation_id}/cancel", operation_id="cancelReservation", response_model=ReservationOut)
def cancel_reservation(
    reservation_id: int, user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> ReservationOut:
    reservation, created = service.cancel(db, user, reservation_id)
    notifications.schedule_delivery(background, db, created)
    return service.to_out(db, reservation)


@router.post(
    "/{reservation_id}/reschedule",
    operation_id="rescheduleReservation",
    response_model=ReservationOut,
    tags=["Approvals"],
)
def reschedule_reservation(
    reservation_id: int, data: RescheduleInput, admin: AdminUser, db: DbSession, background: BackgroundTasks
) -> ReservationOut:
    reservation, created = service.reschedule(db, admin, reservation_id, data.start, data.end)
    notifications.schedule_delivery(background, db, created)
    return service.to_out(db, reservation)
