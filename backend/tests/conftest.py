import os
from pathlib import Path

import pytest

# Trebuie setate înainte de importul aplicației.
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-32-characters")

from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

needs_database = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL lipsește")


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
