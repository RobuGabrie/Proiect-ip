"""Modelele SQLAlchemy. Trebuie să rămână în acord cu db/schema.sql și cu diagrama ERD."""
import enum
from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "pk": "%(table_name)s_pkey",
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
        }
    )


class Role(enum.StrEnum):
    STUDENT = "STUDENT"
    CADRU_DIDACTIC = "CADRU_DIDACTIC"
    CERCETATOR = "CERCETATOR"
    ADMIN = "ADMIN"


class ResourceType(enum.StrEnum):
    SALA = "SALA"
    ECHIPAMENT = "ECHIPAMENT"


class ResourceStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class ReservationStatus(enum.StrEnum):
    PENDING = "PENDING"
    AWAITING_TRAINING = "AWAITING_TRAINING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class NotificationType(enum.StrEnum):
    CERERE_NOUA = "CERERE_NOUA"
    APROBARE = "APROBARE"
    RESPINGERE = "RESPINGERE"
    ANULARE = "ANULARE"
    INSTRUIRE = "INSTRUIRE"
    MENTENANTA = "MENTENANTA"
    LISTA_ASTEPTARE = "LISTA_ASTEPTARE"


def _id_column() -> Mapped[int]:
    return mapped_column(BigInteger, Identity(always=True), primary_key=True)


class ResourceAdmin(Base):
    __tablename__ = "resource_admins"
    __table_args__ = (Index("resource_admins_user_idx", "user_id"),)

    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("users_email_unique", text("lower(email)"), unique=True),)

    id: Mapped[int] = _id_column()
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320))
    nume: Mapped[str] = mapped_column(String(100))
    prenume: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), server_default=Role.STUDENT.value)
    data_creare: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    administered_resources: Mapped[list["Resource"]] = relationship(
        secondary="resource_admins", back_populates="admins"
    )
    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="user", foreign_keys="Reservation.user_id"
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


class ResourceCategory(Base):
    __tablename__ = "resource_categories"

    id: Mapped[int] = _id_column()
    nume: Mapped[str] = mapped_column(String(100), unique=True)
    descriere: Mapped[str | None] = mapped_column(Text)

    resources: Mapped[list["Resource"]] = relationship(back_populates="category")


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint("locuri > 0", name="resources_locuri_check"),
        CheckConstraint("max_echipe_simultane BETWEEN 1 AND 2", name="resources_max_echipe_simultane_check"),
        CheckConstraint(
            "durata_maxima_min > 0 AND durata_maxima_min % 30 = 0", name="resources_durata_maxima_min_check"
        ),
        Index("resources_category_idx", "category_id"),
    )

    id: Mapped[int] = _id_column()
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resource_categories.id", ondelete="RESTRICT"))
    tip: Mapped[ResourceType] = mapped_column(Enum(ResourceType, name="resource_type"))
    nume: Mapped[str] = mapped_column(String(150))
    descriere: Mapped[str | None] = mapped_column(Text)
    locatie: Mapped[str | None] = mapped_column(String(150))
    etaj: Mapped[int | None] = mapped_column(SmallInteger)
    locuri: Mapped[int | None] = mapped_column(Integer)
    echipare: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(150))
    max_echipe_simultane: Mapped[int] = mapped_column(SmallInteger, server_default=text("1"))
    durata_maxima_min: Mapped[int | None] = mapped_column(Integer)
    necesita_instruire: Mapped[bool] = mapped_column(Boolean, server_default=false())
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus, name="resource_status"), server_default=ResourceStatus.ACTIVE.value
    )
    data_creare: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[ResourceCategory] = relationship(back_populates="resources")
    admins: Mapped[list[User]] = relationship(secondary="resource_admins", back_populates="administered_resources")
    schedules: Mapped[list["OperatingSchedule"]] = relationship(back_populates="resource", passive_deletes=True)
    maintenance_windows: Mapped[list["MaintenanceWindow"]] = relationship(
        back_populates="resource", passive_deletes=True
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="resource")


class OperatingSchedule(Base):
    __tablename__ = "operating_schedules"
    __table_args__ = (
        CheckConstraint("zi_saptamana BETWEEN 1 AND 7", name="operating_schedules_zi_saptamana_check"),
        CheckConstraint("ora_deschidere < ora_inchidere", name="operating_schedules_check"),
        CheckConstraint(
            "extract(minute FROM ora_deschidere) IN (0, 30) AND extract(second FROM ora_deschidere) = 0",
            name="operating_schedules_ora_deschidere_check",
        ),
        CheckConstraint(
            "extract(minute FROM ora_inchidere) IN (0, 30) AND extract(second FROM ora_inchidere) = 0",
            name="operating_schedules_ora_inchidere_check",
        ),
        UniqueConstraint(
            "resource_id",
            "zi_saptamana",
            "ora_deschidere",
            name="operating_schedules_resource_id_zi_saptamana_ora_deschidere_key",
        ),
    )

    id: Mapped[int] = _id_column()
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.id", ondelete="CASCADE"))
    zi_saptamana: Mapped[int] = mapped_column(SmallInteger)  # 1 = luni, 7 = duminică
    ora_deschidere: Mapped[time] = mapped_column(Time)
    ora_inchidere: Mapped[time] = mapped_column(Time)

    resource: Mapped[Resource] = relationship(back_populates="schedules")


class MaintenanceWindow(Base):
    __tablename__ = "maintenance_windows"
    __table_args__ = (
        CheckConstraint("data_inceput < data_sfarsit", name="maintenance_windows_check"),
        Index("maintenance_resource_time_idx", "resource_id", "data_inceput", "data_sfarsit"),
    )

    id: Mapped[int] = _id_column()
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.id", ondelete="CASCADE"))
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    data_inceput: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_sfarsit: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    motiv: Mapped[str] = mapped_column(Text)
    anulata_la: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    resource: Mapped[Resource] = relationship(back_populates="maintenance_windows")
    creator: Mapped[User] = relationship()


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (Index("teams_nume_unique", text("lower(nume)"), unique=True),)

    id: Mapped[int] = _id_column()
    nume: Mapped[str] = mapped_column(String(150))

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="team")


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("data_inceput < data_sfarsit", name="reservations_check"),
        # Rezervările sunt formate din sloturi întregi de 30 de minute.
        CheckConstraint(
            "extract(epoch FROM data_inceput)::bigint % 1800 = 0 AND extract(epoch FROM data_sfarsit)::bigint % 1800 = 0",
            name="reservation_slot_30_min",
        ),
        CheckConstraint("status <> 'REJECTED' OR motiv_respingere IS NOT NULL", name="reservation_reject_reason"),
        Index("reservations_resource_time_idx", "resource_id", "data_inceput", "data_sfarsit"),
        Index("reservations_user_idx", "user_id", "status"),
        Index("reservations_team_idx", "team_id"),
    )

    id: Mapped[int] = _id_column()
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.id", ondelete="RESTRICT"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    decided_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    data_inceput: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_sfarsit: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scop: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"), server_default=ReservationStatus.PENDING.value
    )
    prima_rezervare: Mapped[bool] = mapped_column(Boolean, server_default=false())
    necesita_instruire: Mapped[bool] = mapped_column(Boolean, server_default=false())
    necesita_reanalizare: Mapped[bool] = mapped_column(Boolean, server_default=false())
    motiv_respingere: Mapped[str | None] = mapped_column(Text)
    data_creare: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data_decizie: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    resource: Mapped[Resource] = relationship(back_populates="reservations")
    user: Mapped[User] = relationship(back_populates="reservations", foreign_keys=[user_id])
    team: Mapped[Team] = relationship(back_populates="reservations")
    decider: Mapped[User | None] = relationship(foreign_keys=[decided_by])


class ResourceTraining(Base):
    __tablename__ = "resource_trainings"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    confirmed_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    data_finalizare: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        CheckConstraint("data_inceput < data_sfarsit", name="waitlist_entries_check"),
        UniqueConstraint(
            "user_id",
            "resource_id",
            "data_inceput",
            "data_sfarsit",
            name="waitlist_entries_user_id_resource_id_data_inceput_data_sfar_key",
        ),
        Index("waitlist_resource_time_idx", "resource_id", "data_inceput", "data_sfarsit"),
    )

    id: Mapped[int] = _id_column()
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.id", ondelete="CASCADE"))
    data_inceput: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_sfarsit: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_inscriere: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notificat: Mapped[bool] = mapped_column(Boolean, server_default=false())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("notifications_user_idx", "user_id"),)

    id: Mapped[int] = _id_column()
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    reservation_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("reservations.id", ondelete="SET NULL"))
    tip: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"))
    mesaj: Mapped[str] = mapped_column(Text)
    data_trimitere: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="notifications")
    reservation: Mapped[Reservation | None] = relationship()
