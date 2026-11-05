from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.errors import conflict, forbidden, invalid, not_found
from app.models import (
    MaintenanceWindow,
    NotificationType,
    Notification,
    OperatingSchedule,
    Reservation,
    Resource,
    ResourceAdmin,
    ResourceCategory,
    ResourceStatus,
    ResourceType,
    Role,
    User,
)
from app.schemas import (
    CategoryInput,
    MaintenanceWindowInput,
    PersonSummary,
    ResourceInput,
    ResourceOut,
    ScheduleInterval,
)
from app.services import availability, notifications

MAX_AVAILABILITY_DAYS = 31


def get_resource(db: Session, resource_id: int) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise not_found("Resursa nu există.")
    return resource


def is_resource_admin(db: Session, user: User, resource_id: int) -> bool:
    return (
        user.role is Role.ADMIN
        and db.scalar(
            select(ResourceAdmin.user_id).where(
                ResourceAdmin.resource_id == resource_id, ResourceAdmin.user_id == user.id
            )
        )
        is not None
    )


def ensure_resource_admin(db: Session, user: User, resource_id: int) -> None:
    if not is_resource_admin(db, user, resource_id):
        raise forbidden("Doar administratorul resursei poate face această operație.")


def to_out(db: Session, resource: Resource) -> ResourceOut:
    status = resource.status
    now = datetime.now(timezone.utc)
    if status is ResourceStatus.ACTIVE and availability.overlapping_maintenance(
        db, resource.id, now, now + timedelta(seconds=1)
    ):
        status = ResourceStatus.MAINTENANCE
    return ResourceOut(
        id=resource.id,
        category=resource.category,
        tip=resource.tip,
        nume=resource.nume,
        descriere=resource.descriere,
        locatie=resource.locatie,
        etaj=resource.etaj,
        locuri=resource.locuri,
        echipare=resource.echipare,
        model=resource.model,
        max_echipe_simultane=resource.max_echipe_simultane,
        durata_maxima_min=resource.durata_maxima_min,
        necesita_instruire=resource.necesita_instruire,
        status=status,
        administratori=[PersonSummary.model_validate(admin) for admin in resource.admins],
        disponibilitate_curenta=availability.current_availability(db, resource, now),
    )


def list_resources(
    db: Session,
    user: User,
    tip: ResourceType | None,
    category_id: int | None,
    q: str | None,
    current: str | None,
    page: int,
    page_size: int,
) -> tuple[list[ResourceOut], int]:
    query = (
        select(Resource)
        .join(Resource.category)
        .options(selectinload(Resource.category), selectinload(Resource.admins))
        .order_by(Resource.nume)
    )
    if user.role is not Role.ADMIN:
        query = query.where(Resource.status != ResourceStatus.INACTIVE)
    if tip:
        query = query.where(Resource.tip == tip)
    if category_id:
        query = query.where(Resource.category_id == category_id)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                Resource.nume.ilike(pattern),
                Resource.descriere.ilike(pattern),
                Resource.locatie.ilike(pattern),
                ResourceCategory.nume.ilike(pattern),
            )
        )
    items = [to_out(db, resource) for resource in db.scalars(query)]
    if current:
        items = [item for item in items if item.disponibilitate_curenta == current]
    start = (page - 1) * page_size
    return items[start : start + page_size], len(items)


def _load_admins(db: Session, admin_ids: list[int]) -> list[User]:
    admins = list(db.scalars(select(User).where(User.id.in_(admin_ids), User.role == Role.ADMIN)))
    if len(admins) != len(set(admin_ids)):
        raise invalid("Fiecare administrator al resursei trebuie să aibă rolul ADMIN.")
    return admins


def _apply_input(db: Session, resource: Resource, data: ResourceInput) -> None:
    if db.get(ResourceCategory, data.category_id) is None:
        raise invalid("Categoria nu există.")
    resource.admins = _load_admins(db, data.admin_ids)
    for field in ResourceInput.model_fields:
        if field != "admin_ids":
            setattr(resource, field, getattr(data, field))


def create_resource(db: Session, data: ResourceInput) -> Resource:
    resource = Resource()
    _apply_input(db, resource, data)
    db.add(resource)
    db.commit()
    return resource


def update_resource(db: Session, user: User, resource_id: int, data: ResourceInput) -> Resource:
    resource = get_resource(db, resource_id)
    ensure_resource_admin(db, user, resource_id)
    _apply_input(db, resource, data)
    db.commit()
    return resource


def deactivate_resource(db: Session, user: User, resource_id: int) -> None:
    resource = get_resource(db, resource_id)
    ensure_resource_admin(db, user, resource_id)
    resource.status = ResourceStatus.INACTIVE
    db.commit()


def list_categories(db: Session) -> list[ResourceCategory]:
    return list(db.scalars(select(ResourceCategory).order_by(ResourceCategory.nume)))


def _commit_category(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise conflict("CATEGORIE_EXISTENTA", "Există deja o categorie cu acest nume.") from error


def create_category(db: Session, data: CategoryInput) -> ResourceCategory:
    category = ResourceCategory(nume=data.nume, descriere=data.descriere)
    db.add(category)
    _commit_category(db)
    return category


def update_category(db: Session, category_id: int, data: CategoryInput) -> ResourceCategory:
    category = db.get(ResourceCategory, category_id)
    if category is None:
        raise not_found("Categoria nu există.")
    category.nume, category.descriere = data.nume, data.descriere
    _commit_category(db)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = db.get(ResourceCategory, category_id)
    if category is None:
        raise not_found("Categoria nu există.")
    if db.scalar(select(func.count()).select_from(Resource).where(Resource.category_id == category_id)):
        raise conflict("CATEGORIE_CU_RESURSE", "Categoria are resurse asociate și nu poate fi ștearsă.")
    db.delete(category)
    db.commit()


def _format_time(value: time) -> str:
    return value.strftime("%H:%M")


def schedule_out(intervals: list[OperatingSchedule]) -> list[ScheduleInterval]:
    return [
        ScheduleInterval(
            zi_saptamana=interval.zi_saptamana,
            ora_deschidere=_format_time(interval.ora_deschidere),
            ora_inchidere=_format_time(interval.ora_inchidere),
        )
        for interval in intervals
    ]


def get_schedule(db: Session, resource_id: int) -> list[ScheduleInterval]:
    get_resource(db, resource_id)
    return schedule_out(
        list(
            db.scalars(
                select(OperatingSchedule)
                .where(OperatingSchedule.resource_id == resource_id)
                .order_by(OperatingSchedule.zi_saptamana, OperatingSchedule.ora_deschidere)
            )
        )
    )


def replace_schedule(
    db: Session, user: User, resource_id: int, intervals: list[ScheduleInterval]
) -> list[ScheduleInterval]:
    get_resource(db, resource_id)
    ensure_resource_admin(db, user, resource_id)

    ordered = sorted(intervals, key=lambda item: (item.zi_saptamana, item.ora_deschidere))
    for interval in ordered:
        if interval.ora_deschidere >= interval.ora_inchidere:
            raise invalid("Ora de deschidere trebuie să fie înaintea orei de închidere.")
    for previous, following in zip(ordered, ordered[1:]):
        if previous.zi_saptamana == following.zi_saptamana and following.ora_deschidere < previous.ora_inchidere:
            raise invalid("Intervalele din aceeași zi nu se pot suprapune.")

    db.execute(delete(OperatingSchedule).where(OperatingSchedule.resource_id == resource_id))
    db.add_all(
        OperatingSchedule(
            resource_id=resource_id,
            zi_saptamana=interval.zi_saptamana,
            ora_deschidere=time.fromisoformat(interval.ora_deschidere),
            ora_inchidere=time.fromisoformat(interval.ora_inchidere),
        )
        for interval in ordered
    )
    db.commit()
    return get_schedule(db, resource_id)


def get_availability(db: Session, resource_id: int, first_day: date, last_day: date) -> list[dict]:
    resource = get_resource(db, resource_id)
    if last_day < first_day:
        raise invalid("Ultima zi trebuie să fie după prima zi.")
    if (last_day - first_day).days >= MAX_AVAILABILITY_DAYS:
        raise invalid(f"Intervalul poate avea cel mult {MAX_AVAILABILITY_DAYS} de zile.")
    if resource.status is ResourceStatus.INACTIVE:
        return []
    return availability.slots_between(db, resource, first_day, last_day)


def list_maintenance(db: Session, resource_id: int) -> list[MaintenanceWindow]:
    get_resource(db, resource_id)
    return list(
        db.scalars(
            select(MaintenanceWindow)
            .where(MaintenanceWindow.resource_id == resource_id, MaintenanceWindow.anulata_la.is_(None))
            .order_by(MaintenanceWindow.data_inceput)
        )
    )


def create_maintenance(
    db: Session, user: User, resource_id: int, data: MaintenanceWindowInput
) -> tuple[MaintenanceWindow, list[int], list[Notification]]:
    resource = get_resource(db, resource_id)
    ensure_resource_admin(db, user, resource_id)
    if data.data_inceput >= data.data_sfarsit:
        raise invalid("Data de sfârșit trebuie să fie după data de început.")

    window = MaintenanceWindow(
        resource_id=resource_id,
        created_by=user.id,
        data_inceput=data.data_inceput,
        data_sfarsit=data.data_sfarsit,
        motiv=data.motiv,
    )
    db.add(window)
    try:
        db.flush()
    except DBAPIError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) == "RR002":
            raise conflict("SUPRAPUNERE_MENTENANTA", "Intervalul se suprapune cu o altă mentenanță.") from error
        raise

    affected = list(
        db.scalars(
            select(Reservation).where(
                Reservation.resource_id == resource_id,
                Reservation.status.in_(availability.ACTIVE_STATUSES),
                Reservation.data_inceput < data.data_sfarsit,
                Reservation.data_sfarsit > data.data_inceput,
            )
        )
    )
    created: list[Notification] = []
    for reservation in affected:
        reservation.necesita_reanalizare = True
        created += notifications.queue(
            db,
            [reservation.user],
            NotificationType.MENTENANTA,
            f"Rezervarea pentru {resource.nume} este afectată de o mentenanță: {data.motiv}. "
            "Administratorul o va reanaliza.",
            reservation,
        )
    db.commit()
    return window, [reservation.id for reservation in affected], created


def cancel_maintenance(db: Session, user: User, window_id: int) -> None:
    window = db.get(MaintenanceWindow, window_id)
    if window is None or window.anulata_la is not None:
        raise not_found("Perioada de mentenanță nu există.")
    ensure_resource_admin(db, user, window.resource_id)
    window.anulata_la = datetime.now(timezone.utc)
    db.flush()

    flagged = db.scalars(
        select(Reservation).where(
            Reservation.resource_id == window.resource_id,
            Reservation.necesita_reanalizare.is_(True),
            Reservation.data_inceput < window.data_sfarsit,
            Reservation.data_sfarsit > window.data_inceput,
        )
    )
    for reservation in flagged:
        if not availability.overlapping_maintenance(
            db, reservation.resource_id, reservation.data_inceput, reservation.data_sfarsit
        ):
            reservation.necesita_reanalizare = False
    db.commit()
