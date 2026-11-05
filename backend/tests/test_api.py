"""Teste pentru regulile aplicației, pe o bază de date reală (E1-44)."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta

import pytest
import yaml
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from tests.conftest import BACKEND_DIR, needs_database

from app import security
from app.database import get_db
from app.main import app
from app.models import (
    Notification,
    NotificationType,
    Reservation,
    Resource,
    ResourceCategory,
    Role,
    User,
)
from app.services import notifications
from app.services.availability import LOCAL_ZONE

API = "/api/v1"
WEEKDAYS = [1, 2, 3, 4, 5]


def next_monday() -> date:
    today = datetime.now(LOCAL_ZONE).date()
    return today + timedelta(days=7 - today.weekday() + 7)


def at(hour: float, day: date | None = None) -> str:
    whole = int(hour)
    moment = time(whole, 30 if hour != whole else 0)
    return datetime.combine(day or next_monday(), moment, LOCAL_ZONE).isoformat()


@pytest.fixture
def world(alembic_config, engine, monkeypatch):
    command.upgrade(alembic_config, "head")
    factory = sessionmaker(engine, expire_on_commit=False)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(notifications, "send_email", lambda *message: sent.append(message))
    yield World(factory, sent)
    app.dependency_overrides.clear()


class World:
    def __init__(self, factory: sessionmaker, sent: list) -> None:
        self.factory = factory
        self.sent = sent
        self.client = TestClient(app)
        self.admin = self.user("admin", Role.ADMIN)
        self.other_admin = self.user("altadmin", Role.ADMIN)
        self.ana = self.user("ana")
        self.dan = self.user("dan")
        self.eva = self.user("eva")
        with factory() as session:
            category = ResourceCategory(nume="Roboți")
            session.add(category)
            session.commit()
            self.category_id = category.id
        self.robot = self.resource("Robot")
        self.room = self.resource("Sala", max_teams=2, tip="SALA")

    def user(self, name: str, role: Role = Role.STUDENT) -> dict[str, str]:
        with self.factory() as session:
            user = User(google_sub=name, email=f"{name}@student.usv.ro", nume=name.title(), prenume="T", role=role)
            session.add(user)
            session.commit()
            return {
                "id": user.id,
                "email": user.email,
                "headers": {"Authorization": f"Bearer {security.create_access_token(user.id)}"},
            }

    def resource(self, name: str, max_teams: int = 1, tip: str = "ECHIPAMENT", **extra) -> int:
        response = self.client.post(
            f"{API}/resources",
            headers=self.admin["headers"],
            json={
                "categoryId": self.category_id,
                "tip": tip,
                "nume": name,
                "maxEchipeSimultane": max_teams,
                "adminIds": [self.admin["id"]],
                **extra,
            },
        )
        assert response.status_code == 201, response.text
        resource_id = response.json()["id"]
        schedule = [{"ziSaptamana": day, "oraDeschidere": "08:00", "oraInchidere": "20:00"} for day in WEEKDAYS]
        replaced = self.client.put(
            f"{API}/resources/{resource_id}/schedule", headers=self.admin["headers"], json=schedule
        )
        assert replaced.status_code == 200, replaced.text
        return resource_id

    def reserve(self, who: dict, resource_id: int, start: float = 10, end: float = 11, team: str = "Echipa A", day=None):
        return self.client.post(
            f"{API}/reservations",
            headers=who["headers"],
            json={"resourceId": resource_id, "start": at(start, day), "end": at(end, day), "echipa": team},
        )

    def reservation(self, who: dict, resource_id: int, **kwargs) -> int:
        response = self.reserve(who, resource_id, **kwargs)
        assert response.status_code == 201, response.text
        self.sent.clear()
        return response.json()["id"]

    def post(self, path: str, who: dict, **json):
        return self.client.post(f"{API}{path}", headers=who["headers"], json=json or None)

    def get(self, path: str, who: dict, **params):
        return self.client.get(f"{API}{path}", headers=who["headers"], params=params)


pytestmark = needs_database


def code(response) -> str:
    return response.json()["code"]


# --- Contract ---


def test_every_operation_in_the_spec_is_implemented():
    spec = yaml.safe_load((BACKEND_DIR.parent / "docs/api/openapi.yaml").read_text(encoding="utf-8"))
    methods = ("get", "post", "put", "patch", "delete")
    # Numele parametrilor de cale nu ajung la client, doar poziția lor.
    normalize = lambda path: re.sub(r"\{[^}]+\}", "{}", path)
    expected = {
        (method, normalize(path), item[method]["operationId"])
        for path, item in spec["paths"].items()
        for method in methods
        if method in item
    }
    actual = {
        (method, normalize(path.removeprefix(API)), operation["operationId"])
        for path, item in app.openapi()["paths"].items()
        for method, operation in item.items()
    }

    assert actual == expected


@pytest.mark.parametrize("method,path", [("get", "/resources"), ("get", "/reservations"), ("get", "/categories"), ("get", "/waitlist")])
def test_protected_routes_need_authentication(method, path):
    response = getattr(TestClient(app), method)(f"{API}{path}")

    assert response.status_code == 401
    assert code(response) == "NEAUTENTIFICAT"


# --- Roluri ---


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/categories", {"nume": "X"}),
        ("post", "/resources", {}),
        ("get", "/users", None),
        ("get", "/approvals", None),
        ("get", "/approvals/stats", None),
    ],
)
def test_students_cannot_use_admin_routes(world, method, path, payload):
    kwargs = {"json": payload} if payload is not None else {}

    response = world.client.request(method, f"{API}{path}", headers=world.ana["headers"], **kwargs)

    assert response.status_code == 403
    assert code(response) == "ACCES_INTERZIS"


def test_admin_of_another_resource_cannot_decide(world):
    reservation = world.reservation(world.ana, world.robot)

    response = world.post(f"/approvals/{reservation}/approve", world.other_admin)

    assert response.status_code == 403


def test_user_cannot_set_their_own_role_through_the_profile(world):
    response = world.client.patch(
        f"{API}/users/me", headers=world.ana["headers"], json={"prenume": "Ana", "role": "ADMIN"}
    )

    assert response.status_code == 200
    assert response.json()["prenume"] == "Ana"
    assert response.json()["role"] == "STUDENT"


def test_admin_changes_roles_but_not_of_someone_administering_resources(world):
    promoted = world.client.put(f"{API}/users/{world.ana['id']}/role", headers=world.admin["headers"], json={"role": "ADMIN"})
    refused = world.client.put(f"{API}/users/{world.admin['id']}/role", headers=world.admin["headers"], json={"role": "STUDENT"})
    denied = world.client.put(f"{API}/users/{world.dan['id']}/role", headers=world.dan["headers"], json={"role": "ADMIN"})

    assert promoted.json()["role"] == "ADMIN"
    assert refused.status_code == 409
    assert code(refused) == "ADMIN_CU_RESURSE"
    assert denied.status_code == 403


# --- Categorii și resurse ---


def test_category_lifecycle(world):
    created = world.post("/categories", world.admin, nume="Imprimante", descriere="3D")
    duplicate = world.post("/categories", world.admin, nume="Imprimante")
    category_id = created.json()["id"]
    renamed = world.client.put(f"{API}/categories/{category_id}", headers=world.admin["headers"], json={"nume": "Printere"})
    deleted = world.client.delete(f"{API}/categories/{category_id}", headers=world.admin["headers"])

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert renamed.json()["nume"] == "Printere"
    assert deleted.status_code == 204


def test_category_with_resources_cannot_be_deleted(world):
    response = world.client.delete(f"{API}/categories/{world.category_id}", headers=world.admin["headers"])

    assert response.status_code == 409
    assert code(response) == "CATEGORIE_CU_RESURSE"


def test_catalog_filters(world):
    rooms = world.get("/resources", world.ana, tip="SALA").json()
    found = world.get("/resources", world.ana, q="obot").json()
    by_category = world.get("/resources", world.ana, q="roboți").json()
    free = world.get("/resources", world.ana, disponibilitate="LIBERA").json()
    page = world.get("/resources", world.ana, pageSize=1, page=2).json()

    assert [item["nume"] for item in rooms["items"]] == ["Sala"]
    assert [item["nume"] for item in found["items"]] == ["Robot"]
    assert by_category["total"] == 2
    assert free["total"] == 2
    assert (page["total"], len(page["items"]), page["items"][0]["nume"]) == (2, 1, "Sala")


def test_resource_validation(world):
    base = {"categoryId": world.category_id, "tip": "SALA", "nume": "X", "adminIds": [world.admin["id"]]}
    too_many = world.post("/resources", world.admin, **{**base, "maxEchipeSimultane": 3})
    no_admin = world.post("/resources", world.admin, **{**base, "adminIds": []})
    student_admin = world.post("/resources", world.admin, **{**base, "adminIds": [world.ana["id"]]})
    bad_duration = world.post("/resources", world.admin, **{**base, "durataMaximaMin": 45})

    assert [too_many.status_code, no_admin.status_code, student_admin.status_code, bad_duration.status_code] == [400] * 4


def test_only_the_resource_admin_edits_it(world):
    payload = {"categoryId": world.category_id, "tip": "SALA", "nume": "Nou", "adminIds": [world.admin["id"]]}

    edited = world.client.put(f"{API}/resources/{world.room}", headers=world.admin["headers"], json=payload)
    refused = world.client.put(f"{API}/resources/{world.room}", headers=world.other_admin["headers"], json=payload)

    assert edited.json()["nume"] == "Nou"
    assert refused.status_code == 403


def test_deactivated_resource_disappears_for_students_and_cannot_be_booked(world):
    response = world.client.delete(f"{API}/resources/{world.robot}", headers=world.admin["headers"])

    assert response.status_code == 204
    assert [item["nume"] for item in world.get("/resources", world.ana).json()["items"]] == ["Sala"]
    assert world.get("/resources", world.admin).json()["total"] == 2
    assert code(world.reserve(world.ana, world.robot)) == "RESURSA_INACTIVA"


# --- Program și disponibilitate ---


def test_schedule_validation_and_replacement(world):
    path = f"{API}/resources/{world.robot}/schedule"
    headers = world.admin["headers"]
    backwards = world.client.put(path, headers=headers, json=[{"ziSaptamana": 1, "oraDeschidere": "12:00", "oraInchidere": "08:00"}])
    overlap = world.client.put(
        path,
        headers=headers,
        json=[
            {"ziSaptamana": 1, "oraDeschidere": "08:00", "oraInchidere": "12:00"},
            {"ziSaptamana": 1, "oraDeschidere": "11:00", "oraInchidere": "14:00"},
        ],
    )
    unaligned = world.client.put(path, headers=headers, json=[{"ziSaptamana": 1, "oraDeschidere": "08:15", "oraInchidere": "12:00"}])
    two_parts = [
        {"ziSaptamana": 1, "oraDeschidere": "08:00", "oraInchidere": "12:00"},
        {"ziSaptamana": 1, "oraDeschidere": "12:00", "oraInchidere": "14:00"},
    ]
    replaced = world.client.put(path, headers=headers, json=two_parts)
    refused = world.client.put(path, headers=world.ana["headers"], json=two_parts)

    assert [backwards.status_code, overlap.status_code, unaligned.status_code] == [400, 400, 400]
    assert replaced.json() == two_parts
    assert world.get(f"/resources/{world.robot}/schedule", world.ana).json() == two_parts
    assert refused.status_code == 403


def test_availability_reports_each_state(world):
    day = next_monday()
    world.reservation(world.ana, world.room, start=10, end=11)
    world.reservation(world.dan, world.room, start=10, end=10.5)
    world.post(
        f"/resources/{world.room}/maintenance-windows",
        world.admin,
        dataInceput=at(15),
        dataSfarsit=at(16),
        motiv="Curățenie",
    )

    slots = world.get(f"/resources/{world.room}/availability", world.ana, **{"from": day, "to": day}).json()
    by_start = {datetime.fromisoformat(slot["start"]).astimezone(LOCAL_ZONE).strftime("%H:%M"): slot for slot in slots}

    assert len(slots) == 24
    assert min(by_start) == "08:00" and max(by_start) == "19:30"
    assert (by_start["10:00"]["status"], by_start["10:00"]["locuriOcupate"]) == ("OCUPAT", 2)
    assert by_start["10:30"]["status"] == "PARTIAL"
    assert by_start["11:00"]["status"] == "LIBER"
    assert by_start["15:00"]["status"] == "MENTENANTA"


def test_availability_has_no_slots_in_the_weekend_and_limits_the_range(world):
    saturday = next_monday() + timedelta(days=5)
    weekend = world.get(f"/resources/{world.room}/availability", world.ana, **{"from": saturday, "to": saturday})
    too_long = world.get(
        f"/resources/{world.room}/availability", world.ana, **{"from": saturday, "to": saturday + timedelta(days=40)}
    )
    backwards = world.get(
        f"/resources/{world.room}/availability", world.ana, **{"from": saturday, "to": saturday - timedelta(days=1)}
    )

    assert weekend.json() == []
    assert too_long.status_code == 400
    assert backwards.status_code == 400


# --- Rezervări ---


def test_create_reservation_starts_pending_and_notifies_the_admin(world):
    response = world.reserve(world.ana, world.robot)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["primaRezervare"] is True
    assert body["echipa"] == "Echipa A"
    assert [message[0] for message in world.sent] == [world.admin["email"]]


def test_notification_records_when_it_was_sent(world):
    world.reserve(world.ana, world.robot)

    with world.factory() as session:
        notification = session.scalar(select(Notification))
        assert notification.tip is NotificationType.CERERE_NOUA
        assert notification.data_trimitere is not None


def test_email_failure_does_not_break_the_request(world, monkeypatch):
    def fail(*_):
        raise OSError("smtp down")

    monkeypatch.setattr(notifications, "send_email", fail)

    response = world.reserve(world.ana, world.robot)

    assert response.status_code == 201
    with world.factory() as session:
        assert session.scalar(select(Notification)).data_trimitere is None


@pytest.mark.parametrize(
    "start,end,status,expected",
    [
        (11, 10, 400, "DATE_INVALIDE"),
        (7, 9, 422, "IN_AFARA_PROGRAMULUI"),
        (19, 21, 422, "IN_AFARA_PROGRAMULUI"),
    ],
)
def test_interval_rules(world, start, end, status, expected):
    response = world.reserve(world.ana, world.robot, start=start, end=end)

    assert response.status_code == status
    assert code(response) == expected


def test_interval_must_use_30_minute_slots(world):
    response = world.client.post(
        f"{API}/reservations",
        headers=world.ana["headers"],
        json={"resourceId": world.robot, "start": at(10)[:14] + "15" + at(10)[16:], "end": at(11), "echipa": "A"},
    )

    assert response.status_code == 400


def test_interval_needs_a_timezone(world):
    response = world.client.post(
        f"{API}/reservations",
        headers=world.ana["headers"],
        json={"resourceId": world.robot, "start": "2030-01-07T10:00:00", "end": "2030-01-07T11:00:00", "echipa": "A"},
    )

    assert response.status_code == 400


def test_weekend_and_past_are_refused(world):
    saturday = world.reserve(world.ana, world.robot, day=next_monday() + timedelta(days=5))
    past = world.reserve(world.ana, world.robot, day=date(2020, 1, 6))

    assert code(saturday) == "IN_AFARA_PROGRAMULUI"
    assert code(past) == "DATA_TRECUTA"


def test_unknown_resource(world):
    assert world.reserve(world.ana, 999999).status_code == 404


def test_maximum_duration_is_enforced_when_set(world):
    limited = world.resource("Limitat", durataMaximaMin=60)

    assert world.reserve(world.ana, limited, start=10, end=11).status_code == 201
    assert code(world.reserve(world.ana, limited, start=12, end=13.5)) == "DURATA_DEPASITA"


def test_capacity_one_refuses_the_second_team(world):
    world.reserve(world.ana, world.robot)

    response = world.reserve(world.dan, world.robot, start=10.5, end=11.5)

    assert response.status_code == 409
    assert code(response) == "SLOT_OCUPAT"


def test_capacity_two_counts_each_slot_not_total_overlaps(world):
    assert world.reserve(world.ana, world.room, start=8, end=9).status_code == 201
    assert world.reserve(world.dan, world.room, start=9, end=10).status_code == 201

    long_booking = world.reserve(world.eva, world.room, start=8, end=10)
    third = world.reserve(world.eva, world.room, start=9.5, end=10)

    assert long_booking.status_code == 201
    assert third.status_code == 409


def test_simultaneous_requests_cannot_overbook(world):
    def attempt(who):
        client = TestClient(app)
        return client.post(
            f"{API}/reservations",
            headers=who["headers"],
            json={"resourceId": world.robot, "start": at(10), "end": at(11), "echipa": "X"},
        ).status_code

    with ThreadPoolExecutor(max_workers=3) as pool:
        codes = sorted(pool.map(attempt, [world.ana, world.dan, world.eva]))

    assert codes == [201, 409, 409]


def test_team_names_are_shared_ignoring_case(world):
    first = world.reserve(world.ana, world.room, start=8, end=9, team="Echipa Robotică").json()
    second = world.reserve(world.dan, world.room, start=9, end=10, team="echipa robotică").json()

    assert first["echipa"] == second["echipa"] == "Echipa Robotică"


def test_first_booking_flag_clears_after_an_approved_one(world):
    first = world.reservation(world.ana, world.room, start=8, end=9)
    world.post(f"/approvals/{first}/approve", world.admin)

    second = world.reserve(world.ana, world.room, start=9, end=10).json()
    someone_else = world.reserve(world.dan, world.room, start=10, end=11).json()

    assert second["primaRezervare"] is False
    assert someone_else["primaRezervare"] is True


def test_my_reservations_only_show_mine_and_filter(world):
    mine = world.reservation(world.ana, world.room, start=8, end=9)
    world.reservation(world.dan, world.room, start=9, end=10)
    world.post(f"/approvals/{mine}/approve", world.admin)

    all_mine = world.get("/reservations", world.ana).json()
    approved = world.get("/reservations", world.ana, status="APPROVED").json()
    pending = world.get("/reservations", world.ana, status="PENDING").json()
    search = world.get("/reservations", world.ana, q="sal").json()
    by_date = world.get("/reservations", world.ana, q=next_monday().strftime("%d.%m")).json()

    assert [item["id"] for item in all_mine["items"]] == [mine]
    assert approved["total"] == 1
    assert pending["total"] == 0
    assert search["total"] == 1
    assert by_date["total"] == 1


def test_reservation_details_are_private(world):
    reservation = world.reservation(world.ana, world.robot)

    assert world.get(f"/reservations/{reservation}", world.ana).status_code == 200
    assert world.get(f"/reservations/{reservation}", world.admin).status_code == 200
    assert world.get(f"/reservations/{reservation}", world.dan).status_code == 403
    assert world.get(f"/reservations/{reservation}", world.other_admin).status_code == 403


# --- Anulare ---


def test_owner_cancels_and_the_place_is_free_again(world):
    reservation = world.reservation(world.ana, world.robot)

    cancelled = world.post(f"/reservations/{reservation}/cancel", world.ana)
    again = world.reserve(world.dan, world.robot)

    assert cancelled.json()["status"] == "CANCELLED"
    assert again.status_code == 201


def test_strangers_cannot_cancel(world):
    reservation = world.reservation(world.ana, world.robot)

    assert world.post(f"/reservations/{reservation}/cancel", world.dan).status_code == 403


def test_admin_cancels_and_the_requester_is_told(world):
    reservation = world.reservation(world.ana, world.robot)

    response = world.post(f"/reservations/{reservation}/cancel", world.admin)

    assert response.status_code == 200
    assert [message[0] for message in world.sent] == [world.ana["email"]]


def test_cancelling_twice_is_refused(world):
    reservation = world.reservation(world.ana, world.robot)
    world.post(f"/reservations/{reservation}/cancel", world.ana)

    response = world.post(f"/reservations/{reservation}/cancel", world.ana)

    assert response.status_code == 409
    assert code(response) == "TRANZITIE_INTERZISA"


def started_reservation(world, who) -> int:
    """O rezervare în desfășurare: se creează în viitor și se mută în trecut direct în bază."""
    reservation = world.reservation(who, world.room, start=8, end=9)
    world.post(f"/approvals/{reservation}/approve", world.admin)
    now = datetime.now(LOCAL_ZONE)
    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    with world.factory() as session:
        row = session.get(Reservation, reservation)
        row.data_inceput, row.data_sfarsit = start, start + timedelta(hours=3)
        session.commit()
    return reservation


def test_owner_cannot_cancel_after_the_start_but_the_admin_can(world):
    reservation = started_reservation(world, world.ana)

    refused = world.post(f"/reservations/{reservation}/cancel", world.ana)
    allowed = world.post(f"/reservations/{reservation}/cancel", world.admin)

    assert refused.status_code == 409
    assert allowed.status_code == 200


def test_finished_reservations_become_completed(world):
    reservation = started_reservation(world, world.ana)
    with world.factory() as session:
        row = session.get(Reservation, reservation)
        row.data_sfarsit = row.data_inceput + timedelta(minutes=30)
        session.commit()

    body = world.get("/reservations", world.ana).json()

    assert body["items"][0]["status"] == "COMPLETED"


# --- Aprobare și instruire ---


def test_approval_notifies_the_requester(world):
    reservation = world.reservation(world.ana, world.robot)

    response = world.post(f"/approvals/{reservation}/approve", world.admin)

    assert response.json()["status"] == "APPROVED"
    assert response.json()["dataDecizie"]
    assert [message[0] for message in world.sent] == [world.ana["email"]]
    assert "aprobată" in world.sent[0][2]


def test_rejection_needs_a_reason(world):
    reservation = world.reservation(world.ana, world.robot)

    missing = world.post(f"/approvals/{reservation}/reject", world.admin)
    blank = world.post(f"/approvals/{reservation}/reject", world.admin, motiv="   ")
    done = world.post(f"/approvals/{reservation}/reject", world.admin, motiv="Sală ocupată")

    assert missing.status_code == 400
    assert blank.status_code == 400
    assert done.json()["status"] == "REJECTED"
    assert done.json()["motivRespingere"] == "Sală ocupată"
    assert "Sală ocupată" in world.sent[0][2]


def test_rejection_frees_the_place(world):
    reservation = world.reservation(world.ana, world.robot)
    world.post(f"/approvals/{reservation}/reject", world.admin, motiv="Nu")

    assert world.reserve(world.dan, world.robot).status_code == 201


def test_cannot_decide_a_request_cancelled_in_the_meantime(world):
    reservation = world.reservation(world.ana, world.robot)
    world.post(f"/reservations/{reservation}/cancel", world.ana)

    approved = world.post(f"/approvals/{reservation}/approve", world.admin)
    rejected = world.post(f"/approvals/{reservation}/reject", world.admin, motiv="Nu")
    training = world.post(f"/approvals/{reservation}/require-training", world.admin)

    assert [approved.status_code, rejected.status_code, training.status_code] == [409, 409, 409]
    assert code(approved) == "TRANZITIE_INTERZISA"


def test_training_flow(world):
    reservation = world.reservation(world.ana, world.robot)

    conditioned = world.post(f"/approvals/{reservation}/require-training", world.admin)
    early_approval = world.post(f"/approvals/{reservation}/approve", world.admin)
    confirmed = world.post(f"/approvals/{reservation}/complete-training", world.admin)
    approved = world.post(f"/approvals/{reservation}/approve", world.admin)

    assert conditioned.json()["status"] == "AWAITING_TRAINING"
    assert conditioned.json()["necesitaInstruire"] is True
    assert early_approval.status_code == 422
    assert code(early_approval) == "INSTRUIRE_NEFINALIZATA"
    assert confirmed.json()["status"] == "AWAITING_TRAINING"
    assert confirmed.json()["instruireFinalizata"] is True
    assert approved.json()["status"] == "APPROVED"


def test_training_only_applies_while_awaiting(world):
    reservation = world.reservation(world.ana, world.robot)

    assert world.post(f"/approvals/{reservation}/complete-training", world.admin).status_code == 409


def test_training_is_remembered_for_the_next_request(world):
    first = world.reservation(world.ana, world.room, start=8, end=9)
    world.post(f"/approvals/{first}/require-training", world.admin)
    world.post(f"/approvals/{first}/complete-training", world.admin)

    second = world.reserve(world.ana, world.room, start=9, end=10).json()

    assert second["instruireFinalizata"] is True


def test_awaiting_training_can_be_rejected_or_cancelled(world):
    first = world.reservation(world.ana, world.room, start=8, end=9)
    second = world.reservation(world.dan, world.room, start=8, end=9)
    world.post(f"/approvals/{first}/require-training", world.admin)
    world.post(f"/approvals/{second}/require-training", world.admin)

    rejected = world.post(f"/approvals/{first}/reject", world.admin, motiv="Instruire nefinalizată")
    cancelled = world.post(f"/reservations/{second}/cancel", world.dan)

    assert rejected.json()["status"] == "REJECTED"
    assert cancelled.json()["status"] == "CANCELLED"


def test_approvals_list_only_my_resources_and_filters(world):
    world.reservation(world.ana, world.robot)
    other = world.resource("Altceva")
    with world.factory() as session:
        session.get(Resource, other).admins = [session.get(User, world.other_admin["id"])]
        session.commit()
    world.reservation(world.dan, other)

    mine = world.get("/approvals", world.admin).json()
    theirs = world.get("/approvals", world.other_admin).json()
    by_person = world.get("/approvals", world.admin, q="ana").json()
    nobody = world.get("/approvals", world.admin, q="dan").json()
    rejected = world.get("/approvals", world.admin, status="REJECTED").json()

    assert [item["resource"]["nume"] for item in mine["items"]] == ["Robot"]
    assert [item["resource"]["nume"] for item in theirs["items"]] == ["Altceva"]
    assert by_person["total"] == 1
    assert nobody["total"] == 0
    assert rejected["total"] == 0


def test_stats(world):
    today = datetime.now(LOCAL_ZONE).date()
    world.reservation(world.ana, world.room, start=8, end=9)
    approved = world.reservation(world.dan, world.room, start=9, end=10)
    world.post(f"/approvals/{approved}/approve", world.admin)
    with world.factory() as session:
        row = session.get(Reservation, approved)
        end_of_day = datetime.combine(today, time(23, 30), LOCAL_ZONE)
        row.data_inceput, row.data_sfarsit = end_of_day - timedelta(minutes=30), end_of_day
        session.commit()

    stats = world.get("/approvals/stats", world.admin).json()

    assert stats == {"inAsteptare": 1, "aprobateLunaAceasta": 1, "resurseRezervateAzi": 1}


def test_team_usage_counts_decided_bookings_only(world):
    day = next_monday()
    first = world.reservation(world.ana, world.room, start=8, end=10, team="Alfa")
    second = world.reservation(world.dan, world.room, start=10, end=10.5, team="Alfa")
    world.reservation(world.eva, world.room, start=11, end=12, team="Beta")
    for reservation in (first, second):
        world.post(f"/approvals/{reservation}/approve", world.admin)

    usage = world.get("/approvals/usage", world.admin, **{"from": day, "to": day}).json()
    refused = world.get("/approvals/usage", world.other_admin, **{"from": day, "to": day, "resourceId": world.room})

    assert [(row["echipa"], row["numarRezervari"], row["oreRezervate"]) for row in usage] == [("Alfa", 2, 2.5)]
    assert refused.status_code == 403


# --- Mentenanță ---


def maintenance(world, resource_id, start=10, end=12, who=None, motiv="Calibrare"):
    return world.post(
        f"/resources/{resource_id}/maintenance-windows",
        who or world.admin,
        dataInceput=at(start),
        dataSfarsit=at(end),
        motiv=motiv,
    )


def test_maintenance_blocks_new_requests(world):
    assert maintenance(world, world.robot).status_code == 201

    response = world.reserve(world.ana, world.robot, start=11, end=13)

    assert response.status_code == 422
    assert code(response) == "RESURSA_IN_MENTENANTA"
    assert world.reserve(world.ana, world.robot, start=12, end=13).status_code == 201


def test_maintenance_rules(world):
    backwards = maintenance(world, world.robot, start=12, end=10)
    student = maintenance(world, world.robot, who=world.ana)
    stranger = maintenance(world, world.robot, who=world.other_admin)
    no_reason = maintenance(world, world.robot, motiv=" ")
    maintenance(world, world.robot)
    overlapping = maintenance(world, world.robot, start=11, end=13)

    assert backwards.status_code == 400
    assert student.status_code == 403
    assert stranger.status_code == 403
    assert no_reason.status_code == 400
    assert overlapping.status_code == 409
    assert code(overlapping) == "SUPRAPUNERE_MENTENANTA"


def test_maintenance_flags_existing_bookings_and_cancelling_clears_them(world):
    reservation = world.reservation(world.ana, world.robot)

    created = maintenance(world, world.robot).json()
    flagged = world.get("/approvals", world.admin, necesitaReanalizare=True).json()
    approve_during = world.post(f"/approvals/{reservation}/approve", world.admin)
    removed = world.client.delete(f"{API}/maintenance-windows/{created['id']}", headers=world.admin["headers"])
    after = world.get(f"/reservations/{reservation}", world.ana).json()

    assert created["rezervariDeReanalizat"] == [reservation]
    assert [item["id"] for item in flagged["items"]] == [reservation]
    assert world.ana["email"] in [message[0] for message in world.sent]
    assert code(approve_during) == "RESURSA_IN_MENTENANTA"
    assert removed.status_code == 204
    assert after["necesitaReanalizare"] is False
    assert world.reserve(world.dan, world.robot, start=12, end=13).status_code == 201


def test_cancelled_maintenance_cannot_be_cancelled_again(world):
    created = maintenance(world, world.robot).json()
    path = f"{API}/maintenance-windows/{created['id']}"

    assert world.client.delete(path, headers=world.ana["headers"]).status_code == 403
    assert world.client.delete(path, headers=world.admin["headers"]).status_code == 204
    assert world.client.delete(path, headers=world.admin["headers"]).status_code == 404
    assert world.get(f"/resources/{world.robot}/maintenance-windows", world.ana).json() == []


def test_reschedule_moves_a_flagged_booking(world):
    reservation = world.reservation(world.ana, world.robot)
    maintenance(world, world.robot)

    student = world.post(f"/reservations/{reservation}/reschedule", world.dan, start=at(14), end=at(15))
    during = world.post(f"/reservations/{reservation}/reschedule", world.admin, start=at(11), end=at(12))
    moved = world.post(f"/reservations/{reservation}/reschedule", world.admin, start=at(14), end=at(15))

    assert student.status_code == 403
    assert code(during) == "RESURSA_IN_MENTENANTA"
    assert moved.status_code == 200
    assert moved.json()["necesitaReanalizare"] is False
    assert datetime.fromisoformat(moved.json()["start"]).astimezone(LOCAL_ZONE).hour == 14


def test_reschedule_respects_capacity(world):
    reservation = world.reservation(world.ana, world.robot, start=10, end=11)
    world.reservation(world.dan, world.robot, start=14, end=15)

    response = world.post(f"/reservations/{reservation}/reschedule", world.admin, start=at(14), end=at(15))

    assert response.status_code == 409
    assert code(response) == "SLOT_OCUPAT"


# --- Listă de așteptare ---


def join(world, who, resource_id, start=10, end=11):
    return world.post("/waitlist", who, resourceId=resource_id, start=at(start), end=at(end))


def test_waitlist_only_for_full_slots(world):
    assert code(join(world, world.dan, world.robot)) == "SLOT_DISPONIBIL"


def test_waitlist_is_told_when_a_cancellation_frees_the_slot(world):
    reservation = world.reservation(world.ana, world.robot)
    entry = join(world, world.dan, world.robot).json()
    duplicate = join(world, world.dan, world.robot)

    world.post(f"/reservations/{reservation}/cancel", world.ana)
    entries = world.get("/waitlist", world.dan).json()

    assert entry["notificat"] is False
    assert duplicate.status_code == 409
    assert code(duplicate) == "DEJA_INSCRIS"
    assert [message[0] for message in world.sent] == [world.dan["email"]]
    assert entries[0]["notificat"] is True


def test_waitlist_is_told_when_a_rejection_frees_the_slot(world):
    reservation = world.reservation(world.ana, world.robot)
    join(world, world.dan, world.robot)

    world.post(f"/approvals/{reservation}/reject", world.admin, motiv="Nu")

    assert world.dan["email"] in [message[0] for message in world.sent]


def test_waitlist_is_not_told_while_the_slot_is_still_full(world):
    first = world.reservation(world.ana, world.room, start=10, end=11)
    world.reservation(world.dan, world.room, start=10, end=11)
    world.reservation(world.eva, world.room, start=11, end=12)
    world.reservation(world.dan, world.room, start=11, end=12, team="B")
    join(world, world.eva, world.room, start=10, end=12)

    world.post(f"/reservations/{first}/cancel", world.ana)

    assert world.eva["email"] not in [message[0] for message in world.sent]


def test_leave_waitlist_is_private(world):
    world.reservation(world.ana, world.robot)
    entry = join(world, world.dan, world.robot).json()
    path = f"{API}/waitlist/{entry['id']}"

    assert world.client.delete(path, headers=world.eva["headers"]).status_code == 403
    assert world.client.delete(path, headers=world.dan["headers"]).status_code == 204
    assert world.client.delete(path, headers=world.dan["headers"]).status_code == 404
