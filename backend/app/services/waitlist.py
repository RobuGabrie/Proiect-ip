from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import conflict, forbidden, invalid, not_found
from app.models import User, WaitlistEntry
from app.schemas import WaitlistEntryOut, WaitlistInput
from app.services import availability
from app.services.resources import get_resource


def to_out(entry: WaitlistEntry) -> WaitlistEntryOut:
    return WaitlistEntryOut(
        id=entry.id,
        resource_id=entry.resource_id,
        start=entry.data_inceput,
        end=entry.data_sfarsit,
        data_inscriere=entry.data_inscriere,
        notificat=entry.notificat,
    )


def list_for_user(db: Session, user: User) -> list[WaitlistEntry]:
    return list(
        db.scalars(
            select(WaitlistEntry).where(WaitlistEntry.user_id == user.id).order_by(WaitlistEntry.data_inceput)
        )
    )


def join(db: Session, user: User, data: WaitlistInput) -> WaitlistEntry:
    resource = get_resource(db, data.resource_id)
    if (
        data.start >= data.end
        or not availability.is_aligned(data.start)
        or not availability.is_aligned(data.end)
    ):
        raise invalid("Intervalul trebuie format din sloturi întregi de 30 de minute.")
    if availability.has_free_place(db, resource, data.start, data.end):
        raise conflict("SLOT_DISPONIBIL", "Intervalul are locuri libere; poți trimite direct o cerere de rezervare.")

    entry = WaitlistEntry(user_id=user.id, resource_id=resource.id, data_inceput=data.start, data_sfarsit=data.end)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise conflict("DEJA_INSCRIS", "Ești deja înscris pe lista de așteptare pentru acest interval.") from error
    return entry


def leave(db: Session, user: User, entry_id: int) -> None:
    entry = db.get(WaitlistEntry, entry_id)
    if entry is None:
        raise not_found("Înscrierea nu există.")
    if entry.user_id != user.id:
        raise forbidden("Nu poți șterge înscrierea altui utilizator.")
    db.delete(entry)
    db.commit()
