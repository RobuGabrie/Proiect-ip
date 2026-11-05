from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from app.models import ReservationStatus, ResourceStatus, ResourceType, Role

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
HalfHour = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):(00|30)$")]


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class PageOut(ApiModel):
    page: int
    page_size: int
    total: int


class GoogleLoginRequest(ApiModel):
    id_token: str = Field(min_length=1)


class UserOut(ApiModel):
    id: int
    email: str
    nume: str
    prenume: str
    role: Role


class UserPage(PageOut):
    items: list[UserOut]


class UserProfileUpdate(ApiModel):
    nume: Annotated[NonEmptyText, StringConstraints(max_length=100)] | None = None
    prenume: Annotated[NonEmptyText, StringConstraints(max_length=100)] | None = None


class UserRoleUpdate(ApiModel):
    role: Role


class AuthResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class PersonSummary(ApiModel):
    id: int
    nume: str
    prenume: str


class CategoryInput(ApiModel):
    nume: Annotated[NonEmptyText, StringConstraints(max_length=100)]
    descriere: str | None = None


class CategoryOut(CategoryInput):
    id: int


class ResourceInput(ApiModel):
    category_id: int
    tip: ResourceType
    nume: Annotated[NonEmptyText, StringConstraints(max_length=150)]
    descriere: str | None = None
    locatie: Annotated[str, StringConstraints(max_length=150)] | None = None
    etaj: int | None = None
    locuri: int | None = Field(default=None, ge=1)
    echipare: str | None = None
    model: Annotated[str, StringConstraints(max_length=150)] | None = None
    max_echipe_simultane: int = Field(default=1, ge=1, le=2)
    durata_maxima_min: int | None = Field(default=None, ge=30, multiple_of=30)
    necesita_instruire: bool = False
    status: ResourceStatus = ResourceStatus.ACTIVE
    admin_ids: list[int] = Field(min_length=1)


class ResourceOut(ApiModel):
    id: int
    category: CategoryOut
    tip: ResourceType
    nume: str
    descriere: str | None
    locatie: str | None
    etaj: int | None
    locuri: int | None
    echipare: str | None
    model: str | None
    max_echipe_simultane: int
    durata_maxima_min: int | None
    necesita_instruire: bool
    status: ResourceStatus
    administratori: list[PersonSummary]
    disponibilitate_curenta: str


class ResourcePage(PageOut):
    items: list[ResourceOut]


class ScheduleInterval(ApiModel):
    zi_saptamana: int = Field(ge=1, le=7)
    ora_deschidere: HalfHour
    ora_inchidere: HalfHour


class SlotOut(ApiModel):
    start: datetime
    end: datetime
    status: str
    locuri_ocupate: int
    locuri_totale: int


class MaintenanceWindowInput(ApiModel):
    data_inceput: AwareDatetime
    data_sfarsit: AwareDatetime
    motiv: NonEmptyText


class MaintenanceWindowOut(ApiModel):
    id: int
    resource_id: int
    data_inceput: datetime
    data_sfarsit: datetime
    motiv: str


class MaintenanceWindowCreated(MaintenanceWindowOut):
    rezervari_de_reanalizat: list[int]


class ReservationInput(ApiModel):
    resource_id: int
    start: AwareDatetime
    end: AwareDatetime
    echipa: Annotated[NonEmptyText, StringConstraints(max_length=150)]
    scop: str | None = None


class ResourceSummary(ApiModel):
    id: int
    nume: str
    tip: ResourceType
    locatie: str | None


class ReservationOut(ApiModel):
    id: int
    resource: ResourceSummary
    solicitant: PersonSummary
    echipa: str
    start: datetime
    end: datetime
    scop: str | None
    status: ReservationStatus
    prima_rezervare: bool
    necesita_instruire: bool
    instruire_finalizata: bool
    necesita_reanalizare: bool
    motiv_respingere: str | None
    data_creare: datetime
    data_decizie: datetime | None


class ReservationPage(PageOut):
    items: list[ReservationOut]


class RescheduleInput(ApiModel):
    start: AwareDatetime
    end: AwareDatetime


class RejectInput(ApiModel):
    motiv: NonEmptyText


class ApprovalStats(ApiModel):
    in_asteptare: int
    aprobate_luna_aceasta: int
    resurse_rezervate_azi: int


class TeamUsage(ApiModel):
    team_id: int
    echipa: str
    numar_rezervari: int
    ore_rezervate: float


class WaitlistInput(ApiModel):
    resource_id: int
    start: AwareDatetime
    end: AwareDatetime


class WaitlistEntryOut(ApiModel):
    id: int
    resource_id: int
    start: datetime
    end: datetime
    data_inscriere: datetime
    notificat: bool
