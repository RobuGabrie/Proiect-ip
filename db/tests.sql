-- Verifică regulile din schema.sql. Se rulează după seed.sql; modificările sunt anulate la final.
-- Orice regulă încălcată oprește scriptul cu o eroare.
\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_room  BIGINT;
    v_solo  BIGINT;
    v_user  BIGINT;
    v_team  BIGINT;
    v_id    BIGINT;
    v_admin BIGINT;
BEGIN
    SELECT id INTO v_room FROM resources WHERE nume = 'B204';              -- capacitate 2
    SELECT id INTO v_solo FROM resources WHERE nume = 'B110';              -- capacitate 1
    SELECT id INTO v_user FROM users WHERE google_sub = 'seed-radu';
    SELECT id INTO v_admin FROM users WHERE google_sub = 'seed-admin-maria';
    SELECT id INTO v_team FROM teams LIMIT 1;

    -- Două rezervări care nu se suprapun între ele, plus una lungă peste ambele: încap în capacitatea 2.
    INSERT INTO reservations (resource_id, user_id, team_id, data_inceput, data_sfarsit)
    VALUES (v_room, v_user, v_team, '2026-12-01 08:00+02', '2026-12-01 09:00+02'),
           (v_room, v_user, v_team, '2026-12-01 09:00+02', '2026-12-01 10:00+02'),
           (v_room, v_user, v_team, '2026-12-01 08:00+02', '2026-12-01 10:00+02');
    RAISE NOTICE 'OK: capacitatea se verifică pe fiecare slot, nu pe totalul suprapunerilor';

    -- A treia echipă în același slot este refuzată.
    BEGIN
        INSERT INTO reservations (resource_id, user_id, team_id, data_inceput, data_sfarsit)
        VALUES (v_room, v_user, v_team, '2026-12-01 09:30+02', '2026-12-01 10:00+02');
        RAISE EXCEPTION 'A treia rezervare trebuia refuzată';
    EXCEPTION WHEN SQLSTATE 'RR001' THEN
        RAISE NOTICE 'OK: a treia echipă este refuzată';
    END;

    -- O rezervare anulată eliberează locul.
    UPDATE reservations SET status = 'CANCELLED'
    WHERE resource_id = v_room AND data_inceput = '2026-12-01 09:00+02';
    INSERT INTO reservations (resource_id, user_id, team_id, data_inceput, data_sfarsit)
    VALUES (v_room, v_user, v_team, '2026-12-01 09:30+02', '2026-12-01 10:00+02');
    RAISE NOTICE 'OK: anularea eliberează locul';

    -- Reactivarea unei rezervări anulate trece din nou prin verificare.
    BEGIN
        UPDATE reservations SET status = 'PENDING'
        WHERE resource_id = v_room AND status = 'CANCELLED' AND data_inceput = '2026-12-01 09:00+02';
        RAISE EXCEPTION 'Reactivarea trebuia refuzată';
    EXCEPTION WHEN SQLSTATE 'RR001' THEN
        RAISE NOTICE 'OK: reactivarea peste capacitate este refuzată';
    END;

    -- O cerere în așteptare ocupă deja locul la o resursă cu capacitatea 1.
    INSERT INTO reservations (resource_id, user_id, team_id, data_inceput, data_sfarsit)
    VALUES (v_solo, v_user, v_team, '2026-12-02 08:00+02', '2026-12-02 09:00+02')
    RETURNING id INTO v_id;
    BEGIN
        INSERT INTO reservations (resource_id, user_id, team_id, data_inceput, data_sfarsit)
        VALUES (v_solo, v_user, v_team, '2026-12-02 08:30+02', '2026-12-02 09:30+02');
        RAISE EXCEPTION 'Slotul ocupat de o cerere PENDING trebuia refuzat';
    EXCEPTION WHEN SQLSTATE 'RR001' THEN
        RAISE NOTICE 'OK: cererile PENDING ocupă capacitatea';
    END;

    -- Aprobarea propriei rezervări nu se numără pe sine.
    UPDATE reservations SET status = 'APPROVED' WHERE id = v_id;
    RAISE NOTICE 'OK: aprobarea reușește';

    -- Interval care nu este multiplu de 30 de minute.
    BEGIN
        INSERT INTO reservations (resource_id, user_id, team_id, data_inceput, data_sfarsit)
        VALUES (v_solo, v_user, v_team, '2026-12-03 08:15+02', '2026-12-03 09:00+02');
        RAISE EXCEPTION 'Intervalul nealiniat trebuia refuzat';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'OK: sunt acceptate doar sloturi de 30 de minute';
    END;

    -- Respingere fără motiv.
    BEGIN
        UPDATE reservations SET status = 'REJECTED' WHERE id = v_id;
        RAISE EXCEPTION 'Respingerea fără motiv trebuia refuzată';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'OK: respingerea cere un motiv';
    END;

    -- Mentenanțe suprapuse; o mentenanță anulată nu mai blochează intervalul.
    INSERT INTO maintenance_windows (resource_id, created_by, data_inceput, data_sfarsit, motiv)
    VALUES (v_solo, v_admin, '2026-12-05 08:00+02', '2026-12-05 12:00+02', 'Test');
    BEGIN
        INSERT INTO maintenance_windows (resource_id, created_by, data_inceput, data_sfarsit, motiv)
        VALUES (v_solo, v_admin, '2026-12-05 11:00+02', '2026-12-05 13:00+02', 'Test');
        RAISE EXCEPTION 'Mentenanța suprapusă trebuia refuzată';
    EXCEPTION WHEN SQLSTATE 'RR002' THEN
        RAISE NOTICE 'OK: mentenanțele active nu se pot suprapune';
    END;
    UPDATE maintenance_windows SET anulata_la = now()
    WHERE resource_id = v_solo AND data_inceput = '2026-12-05 08:00+02';
    INSERT INTO maintenance_windows (resource_id, created_by, data_inceput, data_sfarsit, motiv)
    VALUES (v_solo, v_admin, '2026-12-05 11:00+02', '2026-12-05 13:00+02', 'Test');
    RAISE NOTICE 'OK: mentenanța anulată eliberează intervalul';

    -- Capacitate în afara limitei din cerințe.
    BEGIN
        UPDATE resources SET max_echipe_simultane = 3 WHERE id = v_room;
        RAISE EXCEPTION 'Capacitatea 3 trebuia refuzată';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'OK: capacitatea este între 1 și 2';
    END;

    -- O categorie cu resurse nu poate fi ștearsă (E1-15).
    BEGIN
        DELETE FROM resource_categories WHERE nume = 'Roboți';
        RAISE EXCEPTION 'Ștergerea categoriei trebuia refuzată';
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'OK: categoria cu resurse nu poate fi ștearsă';
    END;
END;
$$;

ROLLBACK;
