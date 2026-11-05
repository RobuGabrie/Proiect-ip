from datetime import datetime, timedelta, timezone

import jwt
import pytest
from alembic import command
from fastapi.testclient import TestClient
from google.auth.exceptions import TransportError
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker
from tests.conftest import needs_database

from app import security
from app.config import settings
from app.database import get_db
from app.main import app
from app.models import User

pytestmark = needs_database

GOOGLE_CLAIMS = {
    "sub": "google-123",
    "email": "ana.pop@student.usv.ro",
    "email_verified": True,
    "hd": "student.usv.ro",
    "given_name": "Ana",
    "family_name": "Pop",
}


@pytest.fixture
def db_factory(alembic_config, engine):
    command.upgrade(alembic_config, "head")
    factory = sessionmaker(engine, expire_on_commit=False)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield factory
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_factory):
    return TestClient(app)


@pytest.fixture
def google(monkeypatch):
    claims = dict(GOOGLE_CLAIMS)
    monkeypatch.setattr(security.id_token, "verify_oauth2_token", lambda *args, **kwargs: claims)
    return claims


def login(client: TestClient):
    return client.post("/api/v1/auth/google", json={"idToken": "google-token"})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_first_login_creates_a_student(client, google):
    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert body["expiresIn"] == settings.jwt_expires_seconds
    assert body["accessToken"]
    assert body["user"]["email"] == "ana.pop@student.usv.ro"
    assert body["user"]["nume"] == "Pop"
    assert body["user"]["prenume"] == "Ana"
    assert body["user"]["role"] == "STUDENT"
    assert set(body["user"]) == {"id", "email", "nume", "prenume", "role"}


def test_second_login_keeps_the_same_user_and_role(client, db_factory, google):
    first = login(client).json()["user"]
    with db_factory() as session:
        session.execute(text("UPDATE users SET role = 'ADMIN'"))
        session.commit()

    second = login(client).json()["user"]

    assert second["id"] == first["id"]
    assert second["role"] == "ADMIN"
    with db_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


def test_login_updates_a_changed_email_but_keeps_the_profile_name(client, db_factory, google):
    login(client)
    with db_factory() as session:
        session.execute(text("UPDATE users SET nume = 'Popescu'"))
        session.commit()
    google["email"] = "ana.nou@student.usv.ro"

    user = login(client).json()["user"]

    assert user["email"] == "ana.nou@student.usv.ro"
    assert user["nume"] == "Popescu"


def test_missing_names_fall_back_to_the_email(client, google):
    del google["given_name"], google["family_name"]

    user = login(client).json()["user"]

    assert user["nume"] == "ana.pop"
    assert user["prenume"] == "ana.pop"


def test_email_of_another_google_account_is_refused(client, google):
    login(client)
    google["sub"] = "google-456"

    response = login(client)

    assert response.status_code == 409
    assert response.json()["code"] == "CONT_EXISTENT"


def test_unverified_email_is_refused(client, db_factory, google):
    google["email_verified"] = False

    response = login(client)

    assert response.status_code == 401
    with db_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "ana@gmail.com", "hd": None},
        {"email": "ana@usv.ro", "hd": "usv.ro"},
        {"email": "ana.pop@student.usv.ro", "hd": None},
        {"email": "ana@student.usv.ro.example.com", "hd": "student.usv.ro"},
        {"email": "ana@gmail.com", "hd": "student.usv.ro"},
    ],
    ids=["gmail", "staff-domain", "personal-account-with-student-email", "lookalike-domain", "mismatched-email"],
)
def test_only_student_accounts_can_sign_in(client, db_factory, google, overrides):
    google.update(overrides)

    response = login(client)

    assert response.status_code == 403
    assert response.json()["code"] == "ACCES_INTERZIS"
    assert "@student.usv.ro" in response.json()["message"]
    with db_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_invalid_google_token_is_refused_by_the_real_verifier(client):
    response = client.post("/api/v1/auth/google", json={"idToken": "not-a-google-token"})

    assert response.status_code == 401
    assert response.json()["code"] == "NEAUTENTIFICAT"


def test_google_outage_is_not_reported_as_a_bad_token(client, monkeypatch):
    def fail(*args, **kwargs):
        raise TransportError("timeout")

    monkeypatch.setattr(security.id_token, "verify_oauth2_token", fail)

    response = login(client)

    assert response.status_code == 503
    assert response.json()["code"] == "GOOGLE_INDISPONIBIL"


def test_missing_id_token_uses_the_api_error_format(client):
    response = client.post("/api/v1/auth/google", json={})

    assert response.status_code == 400
    assert response.json()["code"] == "DATE_INVALIDE"
    assert "idToken" in response.json()["message"]


def test_current_user_with_a_valid_token(client, google):
    body = login(client).json()

    response = client.get("/api/v1/users/me", headers=auth_header(body["accessToken"]))

    assert response.status_code == 200
    assert response.json() == body["user"]


def signed_token(secret: str = settings.jwt_secret, algorithm: str = "HS256", **overrides) -> str:
    payload = {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1), **overrides}
    return jwt.encode(payload, secret, algorithm=algorithm)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Basic abc"},
        auth_header(signed_token(exp=datetime.now(timezone.utc) - timedelta(seconds=1))),
        auth_header(signed_token(secret="another-secret-with-at-least-32-characters")),
        auth_header(jwt.encode({"sub": "1"}, settings.jwt_secret, algorithm="HS256")),
        auth_header(signed_token(sub="abc")),
        auth_header(signed_token(sub="999999")),
    ],
    ids=["missing", "garbage", "wrong-scheme", "expired", "wrong-secret", "no-expiry", "bad-subject", "unknown-user"],
)
def test_current_user_refuses_bad_credentials(client, google, headers):
    login(client)

    response = client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["code"] == "NEAUTENTIFICAT"


def test_unsigned_token_is_refused(client, google):
    login(client)
    token = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, key="", algorithm="none")

    response = client.get("/api/v1/users/me", headers=auth_header(token))

    assert response.status_code == 401


def test_routes_match_the_api_contract():
    paths = app.openapi()["paths"]

    assert paths["/api/v1/auth/google"]["post"]["operationId"] == "loginWithGoogle"
    assert paths["/api/v1/users/me"]["get"]["operationId"] == "getCurrentUser"
