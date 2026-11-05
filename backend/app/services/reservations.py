from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.errors import business_rule, conflict, forbidden, invalid, invalid_transition, not_found
from app.models import (
    Notification,
    NotificationType,
    Reservation,
    ReservationStatus,
    Resource,
    ResourceAdmin,
    ResourceStatus,
    ResourceTraining,
    Team,
    User,
    WaitlistEntry,
)
from app.schemas import ApprovalStats, PersonSummary, ReservationInput, ReservationOut, ResourceSummary, TeamUsage
from app.services import availability, notifications
from app.services.availability import ACTIVE_STATUSES, LOCAL_ZONE
from app.services.resources import ensure_resource_admin, get_resource, is_resource_admin

SLOT_TAKEN_MESSAGE = "Slotul este ocupat. Te poți înscrie pe lista de așteptare."
_RESERVATION_RELATIONS = (
    selectinload(Reservation.resource),
    selectinload(Reservation.user),
    selectinload(Reservation.team),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def describe(reservation: Reservation) -> str:
    start = reservation.data_inceput.astimezone(LOCAL_ZONE)
    end = reservation.data_sfarsit.astimezone(LOCAL_ZONE)
    return f"{reservation.resource.nume}, {start:%d.%m.%Y}, {start:%H:%M} – {end:%H:%M}"


def has_training(db: Session, user_id: int, resource_id: int) -> bool:
    return db.get(ResourceTraining, (user_id, resource_id)) is not None


def to_out(db: Session, reservation: Reservation) -> ReservationOut:
    return ReservationOut(
        id=reservation.id,
        resource=ResourceSummary.model_validate(reservation.resource),
        solicitant=PersonSummary.model_validate(reservation.user),
        echipa=reservation.team.nume,
        start=reservation.data_inceput,
        end=reservation.data_sfarsit,
        scop=reservation.scop,
        status=reservation.status,
        prima_rezervare=reservation.prima_rezervare,
        necesita_instruire=reservation.necesita_instruire,
        instruire_finalizata=has_training(db, reservation.user_id, reservation.resource_id),
        necesita_reanalizare=reservation.necesita_reanalizare,
        motiv_respingere=reservation.motiv_respingere,
        data_creare=reservation.data_creare,
        data_decizie=reservation.data_decizie,
    )


def complete_finished(db: Session) -> None:
    db.execute(
        update(Reservation)
        .where(Reservation.status == ReservationStatus.APPROVED, Reservation.data_sfarsit <= _now())
        .values(status=ReservationStatus.COMPLETED)
    )
    db.commit()


def _ensure_bookable(db: Session, resource: Resource, start: datetime, end: datetime) -> None:
    if start >= end or not availability.is_aligned(start) or not availability.is_aligned(end):
        raise invalid("Intervalul trebuie format din sloturi întregi de 30 de minute.")
    if start <= _now():
        raise business_rule("DATA_TRECUTA", "Nu se pot face rezervări în trecut.")
    if resource.status is not ResourceStatus.ACTIVE:
        raise business_rule("RESURSA_INACTIVA", "Resursa nu este disponibilă pentru rezervări.")
    if availability.overlapping_maintenance(db, resource.id, start, end):
        raise business_rule("RESURSA_IN_MENTENANTA", "Resursa este în mentenanță în intervalul ales.")
    if not availability.within_schedule(db, resource.id, start, end):
        raise business_rule("IN_AFARA_PROGRAMULUI", "Intervalul este în afara programului de funcționare.")
    if resource.durata_maxima_min and (end - start) > timedelta(minutes=resource.durata_maxima_min):
        raise business_rule(
            "DURATA_DEPASITA", f"Durata maximă pentru această resursă este de {resource.durata_maxima_min} de minute."
        )


def _get_or_create_team(db: Session, name: str) -> Team:
    query = select(Team).where(func.lower(Team.nume) == name.lower())
    team = db.scalar(query)
    if team is not None:
        return team
    try:
        with db.begin_nested():
            team = Team(nume=name)
            db.add(team)
    except IntegrityError:
        # Altă cerere a creat între timp aceeași echipă.
        team = db.scalar(query)
    return team


def _is_capacity_error(error: DBAPIError) -> bool:
    return getattr(error.orig, "sqlstate", None) == "RR001"


def create_reservation(db: Session, user: User, data: ReservationInput) -> tuple[Reservation, list[Notification]]:
    resource = get_resource(db, data.resource_id)
    _ensure_bookable(db, resource, data.start, data.end)

    earlier_booking = db.scalar(
        select(
            exists().where(
                Reservation.user_id == user.id,
                Reservation.resource_id == resource.id,
                Reservation.status.in_((ReservationStatus.APPROVED, ReservationStatus.COMPLETED)),
            )
        )
    )
    reservation = Reservation(
        resource=resource,
        user=user,
        team=_get_or_create_team(db, data.echipa),
        data_inceput=data.start,
        data_sfarsit=data.end,
        scop=data.scop,
        prima_rezervare=not earlier_booking,
    )
    db.add(reservation)
    try:
        db.flush()
    except DBAPIError as error:
        db.rollback()
        if _is_capacity_error(error):
            raise conflict("SLOT_OCUPAT", SLOT_TAKEN_MESSAGE) from error
        raise
    created = notifications.queue(
        db,
        resource.admins,
        NotificationType.CERERE_NOUA,
        f"{user.prenume} {user.nume} a cerut rezervarea: {describe(reservation)}.",
        reservation,
    )
    db.commit()
    return reservation, created


def _search_conditions(q: str):
    pattern = f"%{q}%"
    return or_(
        Resource.nume.ilike(pattern),
        User.nume.ilike(pattern),
        User.prenume.ilike(pattern),
        func.to_char(func.timezone(LOCAL_ZONE.key, Reservation.data_inceput), "DD.MM.YYYY").ilike(pattern),
    )


def _paginate(db: Session, query, page: int, page_size: int) -> tuple[list[ReservationOut], int]:
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    reservations = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return [to_out(db, reservation) for reservation in reservations], total


def _base_query():
    return (
        select(Reservation)
        .join(Reservation.resource)
        .join(Reservation.user)
        .options(*_RESERVATION_RELATIONS)
        .order_by(Reservation.data_inceput.desc(), Reservation.id.desc())
    )


def list_for_user(
    db: Session, user: User, status: ReservationStatus | None, q: str | None, page: int, page_size: int
) -> tuple[list[ReservationOut], int]:
    complete_finished(db)
    query = _base_query().where(Reservation.user_id == user.id)
    if status:
        query = query.where(Reservation.status == status)
    if q:
        query = query.where(_search_conditions(q))
    return _paginate(db, query, page, page_size)


def list_for_admin(
    db: Session,
    admin: User,
    status: ReservationStatus | None,
    resource_id: int | None,
    needs_review: bool | None,
    q: str | None,
    page: int,
    page_size: int,
) -> tuple[list[ReservationOut], int]:
    complete_finished(db)
    query = _base_query().where(Reservation.resource_id.in_(_administered_ids(admin)))
    if status:
        query = query.where(Reservation.status == status)
    if resource_id:
        query = query.where(Reservation.resource_id == resource_id)
    if needs_review is not None:
        query = query.where(Reservation.necesita_reanalizare.is_(needs_review))
    if q:
        query = query.where(_search_conditions(q))
    return _paginate(db, query, page, page_size)


def _administered_ids(admin: User):
    return select(ResourceAdmin.resource_id).where(ResourceAdmin.user_id == admin.id)


def _locked(db: Session, reservation_id: int) -> Reservation:
    reservation = db.scalar(select(Reservation).where(Reservation.id == reservation_id).with_for_update())
    if reservation is None:
        raise not_found("Rezervarea nu există.")
    return reservation


def get_visible(db: Session, user: User, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise not_found("Rezervarea nu există.")
    if reservation.user_id != user.id and not is_resource_admin(db, user, reservation.resource_id):
        raise forbidden("Nu ai acces la această rezervare.")
    return reservation


def _release_to_waitlist(db: Session, reservation: Reservation, start: datetime, end: datetime) -> list[Notification]:
    entries = db.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.resource_id == reservation.resource_id,
            WaitlistEntry.notificat.is_(False),
            WaitlistEntry.data_inceput < end,
            WaitlistEntry.data_sfarsit > start,
        )
    ).all()
    created: list[Notification] = []
    for entry in entries:
        if availability.has_free_place(db, reservation.resource, entry.data_inceput, entry.data_sfarsit):
            entry.notificat = True
            created += notifications.queue(
                db,
                [db.get(User, entry.user_id)],
                NotificationType.LISTA_ASTEPTARE,
                f"S-a eliberat un loc pentru {reservation.resource.nume}. Poți trimite o cerere de rezervare.",
            )
    return created


def cancel(db: Session, user: User, reservation_id: int) -> tuple[Reservation, list[Notification]]:
    reservation = _locked(db, reservation_id)
    is_admin = is_resource_admin(db, user, reservation.resource_id)
    if reservation.user_id != user.id and not is_admin:
        raise forbidden("Nu poți anula această rezervare.")
    if reservation.status not in ACTIVE_STATUSES or reservation.data_sfarsit <= _now():
        raise invalid_transition("Rezervarea nu mai poate fi anulată.")
    if not is_admin and reservation.data_inceput <= _now():
        raise invalid_transition("Rezervarea poate fi anulată doar înainte de începerea slotului.")

    reservation.status = ReservationStatus.CANCELLED
    db.flush()
    created = _release_to_waitlist(db, reservation, reservation.data_inceput, reservation.data_sfarsit)
    if reservation.user_id != user.id:
        created += notifications.queue(
            db,
            [reservation.user],
            NotificationType.ANULARE,
            f"Administratorul a anulat rezervarea: {describe(reservation)}.",
            reservation,
        )
    db.commit()
    return reservation, created


def _decide(reservation: Reservation, admin: User, status: ReservationStatus) -> None:
    reservation.status = status
    reservation.decided_by = admin.id
    reservation.data_decizie = _now()


def approve(db: Session, admin: User, reservation_id: int) -> tuple[Reservation, list[Notification]]:
    reservation = _locked(db, reservation_id)
    ensure_resource_admin(db, admin, reservation.resource_id)
    if reservation.status not in (ReservationStatus.PENDING, ReservationStatus.AWAITING_TRAINING):
        raise invalid_transition("Cererea nu mai poate fi aprobată; a fost anulată sau deja procesată.")
    if reservation.status is ReservationStatus.AWAITING_TRAINING and not has_training(
        db, reservation.user_id, reservation.resource_id
    ):
        raise business_rule("INSTRUIRE_NEFINALIZATA", "Instruirea nu a fost confirmată.")
    if reservation.data_inceput <= _now():
        raise business_rule("DATA_TRECUTA", "Intervalul cererii a trecut deja.")
    if availability.overlapping_maintenance(
        db, reservation.resource_id, reservation.data_inceput, reservation.data_sfarsit
    ):
        raise business_rule("RESURSA_IN_MENTENANTA", "Resursa este în mentenanță în intervalul cererii.")

    _decide(reservation, admin, ReservationStatus.APPROVED)
    created = notifications.queue(
        db,
        [reservation.user],
        NotificationType.APROBARE,
        f"Rezervarea ta a fost aprobată: {describe(reservation)}.",
        reservation,
    )
    db.commit()
    return reservation, created


def reject(db: Session, admin: User, reservation_id: int, reason: str) -> tuple[Reservation, list[Notification]]:
    reservation = _locked(db, reservation_id)
    ensure_resource_admin(db, admin, reservation.resource_id)
    if reservation.status not in (ReservationStatus.PENDING, ReservationStatus.AWAITING_TRAINING):
        raise invalid_transition("Cererea nu mai poate fi respinsă; a fost anulată sau deja procesată.")

    reservation.motiv_respingere = reason
    _decide(reservation, admin, ReservationStatus.REJECTED)
    db.flush()
    created = _release_to_waitlist(db, reservation, reservation.data_inceput, reservation.data_sfarsit)
    created += notifications.queue(
        db,
        [reservation.user],
        NotificationType.RESPINGERE,
        f"Rezervarea ta a fost respinsă: {describe(reservation)}. Motiv: {reason}",
        reservation,
    )
    db.commit()
    return reservation, created


def require_training(db: Session, admin: User, reservation_id: int) -> tuple[Reservation, list[Notification]]:
    reservation = _locked(db, reservation_id)
    ensure_resource_admin(db, admin, reservation.resource_id)
    if reservation.status is not ReservationStatus.PENDING:
        raise invalid_transition("Doar o cerere în așteptare poate fi condiționată de instruire.")

    reservation.status = ReservationStatus.AWAITING_TRAINING
    reservation.necesita_instruire = True
    created = notifications.queue(
        db,
        [reservation.user],
        NotificationType.INSTRUIRE,
        f"Pentru rezervarea {describe(reservation)} este necesară o instruire. Contactează administratorul resursei.",
        reservation,
    )
    db.commit()
    return reservation, created


def complete_training(db: Session, admin: User, reservation_id: int) -> tuple[Reservation, list[Notification]]:
    reservation = _locked(db, reservation_id)
    ensure_resource_admin(db, admin, reservation.resource_id)
    if reservation.status is not ReservationStatus.AWAITING_TRAINING:
        raise invalid_transition("Cererea nu așteaptă o instruire.")

    if not has_training(db, reservation.user_id, reservation.resource_id):
        db.add(
            ResourceTraining(
                user_id=reservation.user_id, resource_id=reservation.resource_id, confirmed_by=admin.id
            )
        )
    created = notifications.queue(
        db,
        [reservation.user],
        NotificationType.INSTRUIRE,
        f"Instruirea pentru {reservation.resource.nume} a fost confirmată. Cererea așteaptă aprobarea.",
        reservation,
    )
    db.commit()
    return reservation, created


def reschedule(
    db: Session, admin: User, reservation_id: int, start: datetime, end: datetime
) -> tuple[Reservation, list[Notification]]:
    reservation = _locked(db, reservation_id)
    ensure_resource_admin(db, admin, reservation.resource_id)
    if reservation.status not in ACTIVE_STATUSES:
        raise invalid_transition("Rezervarea nu mai poate fi reprogramată.")
    _ensure_bookable(db, reservation.resource, start, end)

    old_start, old_end = reservation.data_inceput, reservation.data_sfarsit
    reservation.data_inceput, reservation.data_sfarsit = start, end
    reservation.necesita_reanalizare = False
    try:
        db.flush()
    except DBAPIError as error:
        db.rollback()
        if _is_capacity_error(error):
            raise conflict("SLOT_OCUPAT", SLOT_TAKEN_MESSAGE) from error
        raise
    created = notifications.queue(
        db,
        [reservation.user],
        NotificationType.MENTENANTA,
        f"Rezervarea ta a fost reprogramată: {describe(reservation)}.",
        reservation,
    )
    created += _release_to_waitlist(db, reservation, old_start, old_end)
    db.commit()
    return reservation, created


def stats(db: Session, admin: User) -> ApprovalStats:
    complete_finished(db)
    administered = _administered_ids(admin)
    today = datetime.now(LOCAL_ZONE).date()
    day_start = datetime.combine(today, time.min, LOCAL_ZONE)
    day_end = day_start + timedelta(days=1)
    month_start = datetime.combine(today.replace(day=1), time.min, LOCAL_ZONE)

    pending = db.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(Reservation.resource_id.in_(administered), Reservation.status == ReservationStatus.PENDING)
    )
    approved_this_month = db.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(
            Reservation.resource_id.in_(administered),
            Reservation.status.in_((ReservationStatus.APPROVED, ReservationStatus.COMPLETED)),
            Reservation.data_decizie >= month_start,
        )
    )
    booked_today = db.scalar(
        select(func.count(Reservation.resource_id.distinct())).where(
            Reservation.resource_id.in_(administered),
            Reservation.status.in_((ReservationStatus.APPROVED, ReservationStatus.COMPLETED)),
            Reservation.data_inceput < day_end,
            Reservation.data_sfarsit > day_start,
        )
    )
    return ApprovalStats(
        in_asteptare=pending, aprobate_luna_aceasta=approved_this_month, resurse_rezervate_azi=booked_today
    )


def team_usage(db: Session, admin: User, resource_id: int | None, first_day: date, last_day: date) -> list[TeamUsage]:
    if last_day < first_day:
        raise invalid("Ultima zi trebuie să fie după prima zi.")
    if resource_id is not None:
        ensure_resource_admin(db, admin, resource_id)
    range_start = datetime.combine(first_day, time.min, LOCAL_ZONE)
    range_end = datetime.combine(last_day + timedelta(days=1), time.min, LOCAL_ZONE)
    query = (
        select(
            Team.id,
            Team.nume,
            func.count(Reservation.id),
            func.sum(func.extract("epoch", Reservation.data_sfarsit - Reservation.data_inceput)),
        )
        .join(Reservation.team)
        .where(
            Reservation.resource_id.in_(_administered_ids(admin)),
            Reservation.status.in_((ReservationStatus.APPROVED, ReservationStatus.COMPLETED)),
            Reservation.data_inceput < range_end,
            Reservation.data_sfarsit > range_start,
        )
        .group_by(Team.id, Team.nume)
        .order_by(func.sum(func.extract("epoch", Reservation.data_sfarsit - Reservation.data_inceput)).desc())
    )
    if resource_id is not None:
        query = query.where(Reservation.resource_id == resource_id)
    return [
        TeamUsage(team_id=team_id, echipa=name, numar_rezervari=count, ore_rezervate=float(seconds) / 3600)
        for team_id, name, count, seconds in db.execute(query)
    ]
