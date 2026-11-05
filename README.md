# Research Resource Manager

Platformă web pentru programarea resurselor de cercetare dintr-o universitate. Backend FastAPI, frontend Next.js, bază de date PostgreSQL.

## Pornire cu Docker

Necesită Docker Desktop. Comanda pornește baza de date, backend-ul și frontend-ul:

```bash
docker compose up --build
```

- Aplicația: http://localhost:3000
- Documentația API: http://localhost:8000/api/v1/docs

Verificarea regulilor din baza de date:

```bash
docker compose exec -T db psql -U rrm -d rrm -f - < db/tests.sql
```

`docker compose down -v` șterge datele; la următoarea pornire schema și datele de test se încarcă din nou.

## Pornire fără Docker

Necesită Python 3.12, Node.js și un server PostgreSQL cu `db/schema.sql` și `db/seed.sql` încărcate.

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# completați JWT_SECRET în .env
.venv/bin/uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Testele backend-ului: `cd backend && .venv/bin/python -m pytest`

## Autentificare Google

În Google Cloud Console, clientul OAuth trebuie să aibă `http://localhost:3000` la „Authorized JavaScript origins”, altfel butonul de conectare dă eroare.

Sunt acceptate doar conturile instituționale `@student.usv.ro` (setarea `GOOGLE_ALLOWED_DOMAIN`). Orice cont nou primește rolul `STUDENT`. Primul administrator se setează manual, după prima conectare:

```bash
docker compose exec db psql -U rrm -d rrm -c "UPDATE users SET role = 'ADMIN' WHERE email = 'adresa@student.usv.ro'"
```

## Migrări

Modelele sunt în `backend/app/models.py`, iar migrările în `backend/migrations`. După modificarea modelelor:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "descriere"
.venv/bin/alembic upgrade head
```

- Bază de date goală: `.venv/bin/alembic upgrade head` creează schema completă.
- Bază creată din `db/schema.sql` (cazul Docker Compose): rulați o singură dată `.venv/bin/alembic stamp 0001`, altfel prima migrare încearcă să recreeze tabelele.

Testele migrărilor au nevoie de o bază de date goală, separată, și se sar dacă `TEST_DATABASE_URL` lipsește. Conținutul ei este șters la fiecare rulare:

```bash
docker compose exec db createdb -U rrm rrm_test
TEST_DATABASE_URL=postgresql+psycopg://rrm:rrm_dev@localhost:5432/rrm_test .venv/bin/python -m pytest
```

## Documente

- `docs/api/openapi.yaml`: specificația API; se deschide în https://editor.swagger.io/
- `docs/db/erd.png`: diagrama ERD; se regenerează cu `python3 docs/db/generate_erd.py`
- `docs/confluence/laborator-5.md`: conținutul paginii `LABORATOR 5` din Confluence
