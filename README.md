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

Sunt acceptate doar conturile instituționale `@student.usv.ro` (setarea `GOOGLE_ALLOWED_DOMAIN`). Orice cont nou primește rolul `STUDENT`. Primul administrator se setează manual, după prima conectare; comanda îl face administrator al tuturor resurselor:

```bash
docker compose exec -T db psql -U rrm -d rrm -v email="'adresa@student.usv.ro'" -f - < db/make_admin.sql
```

Conectați-vă din nou după comandă. De aici încolo, rolurile se schimbă din pagina Utilizatori.

## Funcționalități

| Rol | Pagini |
| --- | --- |
| Utilizator | Săli, Echipamente, calendarul resursei, Rezervări, Listă de așteptare, Profil |
| Administrator | Aprobări (cu instruire și reprogramare), Săli, Echipamente, Program și mentenanță, Categorii, Utilizare, Utilizatori, Profil |

Emailurile aplicației ajung în inboxul local Mailpit: http://localhost:8025. Pentru emailuri reale, setați `SMTP_HOST` și `SMTP_PORT` către un server SMTP.

Regulile de rezervare: sloturi de 30 de minute, doar în programul resursei, în afara mentenanței și în limita de echipe simultane. Cererile în așteptare ocupă deja locul. Fusul orar al aplicației este `Europe/Bucharest`.

## Migrări

Modelele sunt în `backend/app/models.py`, iar migrările în `backend/migrations`. După modificarea modelelor:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "descriere"
.venv/bin/alembic upgrade head
```

- Bază de date goală: `.venv/bin/alembic upgrade head` creează schema completă.
- Bază creată din `db/schema.sql` (cazul Docker Compose): rulați o singură dată `.venv/bin/alembic stamp 0001`, altfel prima migrare încearcă să recreeze tabelele.

## Teste

Testele care folosesc baza de date se sar dacă `TEST_DATABASE_URL` lipsește. Baza trebuie să fie separată, pentru că este ștearsă la fiecare rulare:

```bash
docker compose exec db createdb -U rrm rrm_test
cd backend
TEST_DATABASE_URL=postgresql+psycopg://rrm:rrm_dev@localhost:5432/rrm_test .venv/bin/python -m pytest
```

Testele end-to-end pornesc aplicația pe porturile 3100 și 8100, în Chromium, folosind `rrm_test`:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

Autentificarea Google nu poate fi automatizată, așa că aceste teste folosesc token-uri create de `backend/scripts/e2e_setup.py`.

## Documente

- `docs/api/openapi.yaml`: specificația API; se deschide în https://editor.swagger.io/
- `docs/db/erd.png`: diagrama ERD; se regenerează cu `python3 docs/db/generate_erd.py`
- `docs/confluence/laborator-5.md`: conținutul paginii `LABORATOR 5` din Confluence
