-- Face un cont existent administrator al tuturor resurselor.
-- Contul trebuie să se fi conectat o dată cu Google.
-- docker compose exec -T db psql -U rrm -d rrm -v email="'adresa@student.usv.ro'" -f - < db/make_admin.sql
\set ON_ERROR_STOP on

BEGIN;

UPDATE users SET role = 'ADMIN' WHERE lower(email) = lower(:email);

INSERT INTO resource_admins (resource_id, user_id)
SELECT r.id, u.id
FROM resources r
CROSS JOIN users u
WHERE lower(u.email) = lower(:email)
ON CONFLICT DO NOTHING;

SELECT email, role, (SELECT count(*) FROM resource_admins ra WHERE ra.user_id = u.id) AS resurse
FROM users u
WHERE lower(email) = lower(:email);

COMMIT;
