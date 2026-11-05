import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Reservation,
    ReservationStatus,
    Resource,
    ResourceCategory,
    ResourceType,
    Team,
    User,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL lipsește")

START = datetime(2026, 12, 1, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def alembic_config():
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
    return config


@pytest.fixture
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    yield engine
    engine.dispose()


def add_resource(session: Session, max_teams: int = 1) -> tuple[Resource, User, Team]:
    resource = Resource(
        category=ResourceCategory(nume="Roboți"),
        tip=ResourceType.ECHIPAMENT,
        nume="Robot colaborativ",
        max_echipe_simultane=max_teams,
    )
    user = User(google_sub="sub-1", email="ana@example.ro", nume="Pop", prenume="Ana")
    team = Team(nume="Echipa Robotică")
    session.add_all([resource, user, team])
    session.flush()
    return resource, user, team


def reservation(resource: Resource, user: User, team: Team, minutes: int = 60) -> Reservation:
    return Reservation(
        resource=resource,
        user=user,
        team=team,
        data_inceput=START,
        data_sfarsit=START + timedelta(minutes=minutes),
    )


def test_upgrade_creates_every_model_table(alembic_config, engine):
    command.upgrade(alembic_config, "head")

    assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())


def test_models_match_the_migration(alembic_config, engine):
    command.upgrade(alembic_config, "head")

    command.check(alembic_config)


def test_models_match_the_lab_schema(alembic_config, engine):
    schema = (BACKEND_DIR.parent / "db" / "schema.sql").read_text(encoding="utf-8")
    raw_connection = engine.raw_connection()
    raw_connection.driver_connection.execute(schema)
    raw_connection.commit()
    raw_connection.close()
    command.stamp(alembic_config, "head")

    command.check(alembic_config)


def test_defaults_come_from_the_database(alembic_config, engine):
    command.upgrade(alembic_config, "head")

    with Session(engine) as session:
        resource, user, team = add_resource(session)
        booking = reservation(resource, user, team)
        session.add(booking)
        session.commit()

        assert booking.status is ReservationStatus.PENDING
        assert booking.prima_rezervare is False
        assert booking.user.reservations == [booking]
        assert booking.resource.category.nume == "Roboți"


def test_capacity_trigger_refuses_an_overbooking(alembic_config, engine):
    command.upgrade(alembic_config, "head")

    with Session(engine) as session:
        resource, user, team = add_resource(session)
        session.add(reservation(resource, user, team))
        session.flush()

        session.add(reservation(resource, user, team))
        with pytest.raises(DBAPIError) as error:
            session.flush()

    assert error.value.orig.sqlstate == "RR001"


def test_rejected_reservation_frees_the_place(alembic_config, engine):
    command.upgrade(alembic_config, "head")

    with Session(engine) as session:
        resource, user, team = add_resource(session)
        first = reservation(resource, user, team)
        session.add(first)
        session.flush()

        first.status = ReservationStatus.REJECTED
        first.motiv_respingere = "Sală ocupată"
        session.add(reservation(resource, user, team))
        session.commit()

        active = session.scalars(select(Reservation).where(Reservation.status == ReservationStatus.PENDING)).all()
        assert len(active) == 1


def test_downgrade_leaves_nothing_behind(alembic_config, engine):
    command.upgrade(alembic_config, "head")

    command.downgrade(alembic_config, "base")

    with engine.connect() as connection:
        types = connection.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'")).scalars().all()
        functions = connection.execute(
            text("SELECT proname FROM pg_proc WHERE pronamespace = 'public'::regnamespace")
        ).scalars().all()
    assert inspect(engine).get_table_names() == ["alembic_version"]
    assert types == []
    assert functions == []
