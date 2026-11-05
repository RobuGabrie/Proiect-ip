from fastapi.testclient import TestClient

from app import database
from app.main import app

client = TestClient(app)


def test_health_when_database_is_available(monkeypatch):
    monkeypatch.setattr(database, "database_is_available", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_when_database_is_unavailable(monkeypatch):
    monkeypatch.setattr(database, "database_is_available", lambda: False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_cors_allows_the_frontend(monkeypatch):
    monkeypatch.setattr(database, "database_is_available", lambda: True)

    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_other_origins(monkeypatch):
    monkeypatch.setattr(database, "database_is_available", lambda: True)

    response = client.get("/health", headers={"Origin": "http://example.com"})

    assert "access-control-allow-origin" not in response.headers
