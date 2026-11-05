from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query

from app.dependencies import AdminUser, DbSession, PageNumber, PageSize
from app.models import ReservationStatus
from app.schemas import ApprovalStats, RejectInput, ReservationOut, ReservationPage, TeamUsage
from app.services import notifications
from app.services import reservations as service

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", operation_id="listApprovals", response_model=ReservationPage)
def list_approvals(
    admin: AdminUser,
    db: DbSession,
    status: ReservationStatus | None = None,
    resource_id: Annotated[int | None, Query(alias="resourceId")] = None,
    needs_review: Annotated[bool | None, Query(alias="necesitaReanalizare")] = None,
    q: str | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> ReservationPage:
    items, total = service.list_for_admin(db, admin, status, resource_id, needs_review, q, page, page_size)
    return ReservationPage(items=items, page=page, page_size=page_size, total=total)


@router.get("/stats", operation_id="getApprovalStats", response_model=ApprovalStats)
def get_approval_stats(admin: AdminUser, db: DbSession) -> ApprovalStats:
    return service.stats(db, admin)


@router.get("/usage", operation_id="getTeamUsage", response_model=list[TeamUsage])
def get_team_usage(
    first_day: Annotated[date, Query(alias="from")],
    last_day: Annotated[date, Query(alias="to")],
    admin: AdminUser,
    db: DbSession,
    resource_id: Annotated[int | None, Query(alias="resourceId")] = None,
) -> list[TeamUsage]:
    return service.team_usage(db, admin, resource_id, first_day, last_day)


@router.post("/{reservation_id}/approve", operation_id="approveReservation", response_model=ReservationOut)
def approve_reservation(
    reservation_id: int, admin: AdminUser, db: DbSession, background: BackgroundTasks
) -> ReservationOut:
    reservation, created = service.approve(db, admin, reservation_id)
    notifications.schedule_delivery(background, db, created)
    return service.to_out(db, reservation)


@router.post("/{reservation_id}/reject", operation_id="rejectReservation", response_model=ReservationOut)
def reject_reservation(
    reservation_id: int, data: RejectInput, admin: AdminUser, db: DbSession, background: BackgroundTasks
) -> ReservationOut:
    reservation, created = service.reject(db, admin, reservation_id, data.motiv)
    notifications.schedule_delivery(background, db, created)
    return service.to_out(db, reservation)


@router.post("/{reservation_id}/require-training", operation_id="requireTraining", response_model=ReservationOut)
def require_training(
    reservation_id: int, admin: AdminUser, db: DbSession, background: BackgroundTasks
) -> ReservationOut:
    reservation, created = service.require_training(db, admin, reservation_id)
    notifications.schedule_delivery(background, db, created)
    return service.to_out(db, reservation)


@router.post("/{reservation_id}/complete-training", operation_id="completeTraining", response_model=ReservationOut)
def complete_training(
    reservation_id: int, admin: AdminUser, db: DbSession, background: BackgroundTasks
) -> ReservationOut:
    reservation, created = service.complete_training(db, admin, reservation_id)
    notifications.schedule_delivery(background, db, created)
    return service.to_out(db, reservation)
