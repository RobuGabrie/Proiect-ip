from fastapi import APIRouter, status

from app.dependencies import CurrentUser, DbSession
from app.schemas import WaitlistEntryOut, WaitlistInput
from app.services import waitlist as service

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.get("", operation_id="listMyWaitlistEntries", response_model=list[WaitlistEntryOut])
def list_my_waitlist_entries(user: CurrentUser, db: DbSession) -> list[WaitlistEntryOut]:
    return [service.to_out(entry) for entry in service.list_for_user(db, user)]


@router.post("", operation_id="joinWaitlist", response_model=WaitlistEntryOut, status_code=status.HTTP_201_CREATED)
def join_waitlist(data: WaitlistInput, user: CurrentUser, db: DbSession) -> WaitlistEntryOut:
    return service.to_out(service.join(db, user, data))


@router.delete("/{entry_id}", operation_id="leaveWaitlist", status_code=status.HTTP_204_NO_CONTENT)
def leave_waitlist(entry_id: int, user: CurrentUser, db: DbSession) -> None:
    service.leave(db, user, entry_id)
