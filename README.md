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
.venv/bin/uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Testele backend-ului: `cd backend && .venv/bin/python -m pytest`

## Documente

- `docs/api/openapi.yaml`: specificația API; se deschide în https://editor.swagger.io/
- `docs/db/erd.png`: diagrama ERD; se regenerează cu `python3 docs/db/generate_erd.py`
- `docs/confluence/laborator-5.md`: conținutul paginii `LABORATOR 5` din Confluence
