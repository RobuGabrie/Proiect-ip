"""Pregătește baza de date pentru testele end-to-end și scrie token-urile conturilor de test.

Șterge tot din baza indicată de DATABASE_URL, deci rulați-l doar pe o bază separată.
"""
import json
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import security  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import User  # noqa: E402

ACCOUNTS = {
    "student": "seed-andrei",
    "researcher": "seed-dan",
    "roomAdmin": "seed-admin-maria",
    "equipmentAdmin": "seed-admin-popescu",
}


def main(output: Path) -> None:
    if not (make_url(settings.database_url).database or "").endswith("_test"):
        sys.exit("Refuz: DATABASE_URL trebuie să indice o bază al cărei nume se termină cu _test.")

    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")

    seed = (BACKEND_DIR.parent / "db" / "seed.sql").read_text(encoding="utf-8")
    raw_connection = engine.raw_connection()
    raw_connection.driver_connection.execute(seed)
    raw_connection.commit()
    raw_connection.close()

    with Session(engine) as session:
        tokens = {
            name: security.create_access_token(session.scalar(select(User.id).where(User.google_sub == sub)))
            for name, sub in ACCOUNTS.items()
        }
    output.write_text(json.dumps(tokens), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
