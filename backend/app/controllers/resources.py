from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.dependencies import AdminUser, CurrentUser, DbSession, PageNumber, PageSize
from app.models import MaintenanceWindow, ResourceType
from app.schemas import (
    MaintenanceWindowCreated,
    MaintenanceWindowInput,
    MaintenanceWindowOut,
    ResourceInput,
    ResourceOut,
    ResourcePage,
    ScheduleInterval,
    SlotOut,
)
from app.services import notifications
from app.services import resources as service

router = APIRouter(tags=["Resources"])


@router.get("/resources", operation_id="listResources", response_model=ResourcePage)
def list_resources(
    user: CurrentUser,
    db: DbSession,
    tip: ResourceType | None = None,
    category_id: Annotated[int | None, Query(alias="categoryId")] = None,
    q: str | None = None,
    disponibilitate: Literal["LIBERA", "REZERVATA"] | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> ResourcePage:
    items, total = service.list_resources(db, user, tip, category_id, q, disponibilitate, page, page_size)
    return ResourcePage(items=items, page=page, page_size=page_size, total=total)


@router.post("/resources", operation_id="createResource", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(data: ResourceInput, _: AdminUser, db: DbSession) -> ResourceOut:
    return service.to_out(db, service.create_resource(db, data))


@router.get("/resources/{resource_id}", operation_id="getResource", response_model=ResourceOut)
def get_resource(resource_id: int, _: CurrentUser, db: DbSession) -> ResourceOut:
    return service.to_out(db, service.get_resource(db, resource_id))


@router.put("/resources/{resource_id}", operation_id="updateResource", response_model=ResourceOut)
def update_resource(resource_id: int, data: ResourceInput, user: CurrentUser, db: DbSession) -> ResourceOut:
    return service.to_out(db, service.update_resource(db, user, resource_id, data))


@router.delete("/resources/{resource_id}", operation_id="deactivateResource", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_resource(resource_id: int, user: CurrentUser, db: DbSession) -> None:
    service.deactivate_resource(db, user, resource_id)


@router.get("/resources/{resource_id}/schedule", operation_id="getResourceSchedule", response_model=list[ScheduleInterval])
def get_resource_schedule(resource_id: int, _: CurrentUser, db: DbSession) -> list[ScheduleInterval]:
    return service.get_schedule(db, resource_id)


@router.put(
    "/resources/{resource_id}/schedule", operation_id="replaceResourceSchedule", response_model=list[ScheduleInterval]
)
def replace_resource_schedule(
    resource_id: int, intervals: list[ScheduleInterval], user: CurrentUser, db: DbSession
) -> list[ScheduleInterval]:
    return service.replace_schedule(db, user, resource_id, intervals)


@router.get("/resources/{resource_id}/availability", operation_id="getResourceAvailability", response_model=list[SlotOut])
def get_resource_availability(
    resource_id: int,
    first_day: Annotated[date, Query(alias="from")],
    last_day: Annotated[date, Query(alias="to")],
    _: CurrentUser,
    db: DbSession,
) -> list[dict]:
    return service.get_availability(db, resource_id, first_day, last_day)


@router.get(
    "/resources/{resource_id}/maintenance-windows",
    operation_id="listMaintenanceWindows",
    response_model=list[MaintenanceWindowOut],
)
def list_maintenance_windows(resource_id: int, _: CurrentUser, db: DbSession) -> list[MaintenanceWindow]:
    return service.list_maintenance(db, resource_id)


@router.post(
    "/resources/{resource_id}/maintenance-windows",
    operation_id="createMaintenanceWindow",
    response_model=MaintenanceWindowCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance_window(
    resource_id: int,
    data: MaintenanceWindowInput,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> MaintenanceWindowCreated:
    window, affected, created = service.create_maintenance(db, user, resource_id, data)
    notifications.schedule_delivery(background, db, created)
    return MaintenanceWindowCreated(
        id=window.id,
        resource_id=window.resource_id,
        data_inceput=window.data_inceput,
        data_sfarsit=window.data_sfarsit,
        motiv=window.motiv,
        rezervari_de_reanalizat=affected,
    )


@router.delete("/maintenance-windows/{window_id}", operation_id="cancelMaintenanceWindow", status_code=status.HTTP_204_NO_CONTENT)
def cancel_maintenance_window(window_id: int, user: CurrentUser, db: DbSession) -> None:
    service.cancel_maintenance(db, user, window_id)
