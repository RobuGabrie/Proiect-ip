-- Research Resource Manager: schema bazei de date PostgreSQL (Laborator 5, 9.7).
-- Pornește de la diagrama de domeniu din Laboratorul 4; diferențele sunt explicate
-- în docs/confluence/laborator-5.md.

CREATE TYPE user_role AS ENUM ('STUDENT', 'CADRU_DIDACTIC', 'CERCETATOR', 'ADMIN');
CREATE TYPE resource_type AS ENUM ('SALA', 'ECHIPAMENT');
CREATE TYPE resource_status AS ENUM ('ACTIVE', 'MAINTENANCE', 'INACTIVE');
CREATE TYPE reservation_status AS ENUM (
    'PENDING', 'AWAITING_TRAINING', 'APPROVED', 'REJECTED', 'CANCELLED', 'COMPLETED'
);
CREATE TYPE notification_type AS ENUM (
    'CERERE_NOUA', 'APROBARE', 'RESPINGERE', 'ANULARE', 'INSTRUIRE', 'MENTENANTA', 'LISTA_ASTEPTARE'
);

CREATE TABLE users (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    google_sub  VARCHAR(255) NOT NULL UNIQUE,
    email       VARCHAR(320) NOT NULL,
    nume        VARCHAR(100) NOT NULL,
    prenume     VARCHAR(100) NOT NULL,
    role        user_role    NOT NULL DEFAULT 'STUDENT',
    data_creare TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX users_email_unique ON users (lower(email));

CREATE TABLE resource_categories (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nume      VARCHAR(100) NOT NULL UNIQUE,
    descriere TEXT
);

CREATE TABLE resources (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id          BIGINT          NOT NULL REFERENCES resource_categories (id) ON DELETE RESTRICT,
    tip                  resource_type   NOT NULL,
    nume                 VARCHAR(150)    NOT NULL,
    descriere            TEXT,
    locatie              VARCHAR(150),
    etaj                 SMALLINT,
    locuri               INTEGER         CHECK (locuri > 0),
    echipare             TEXT,
    model                VARCHAR(150),
    max_echipe_simultane SMALLINT        NOT NULL DEFAULT 1 CHECK (max_echipe_simultane BETWEEN 1 AND 2),
    durata_maxima_min    INTEGER         CHECK (durata_maxima_min > 0 AND durata_maxima_min % 30 = 0),
    necesita_instruire   BOOLEAN         NOT NULL DEFAULT false,
    status               resource_status NOT NULL DEFAULT 'ACTIVE',
    data_creare          TIMESTAMPTZ     NOT NULL DEFAULT now()
);
CREATE INDEX resources_category_idx ON resources (category_id);

CREATE TABLE resource_admins (
    resource_id BIGINT NOT NULL REFERENCES resources (id) ON DELETE CASCADE,
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    PRIMARY KEY (resource_id, user_id)
);
CREATE INDEX resource_admins_user_idx ON resource_admins (user_id);

CREATE TABLE operating_schedules (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id    BIGINT   NOT NULL REFERENCES resources (id) ON DELETE CASCADE,
    zi_saptamana   SMALLINT NOT NULL CHECK (zi_saptamana BETWEEN 1 AND 7), -- 1 = luni, 7 = duminică
    ora_deschidere TIME     NOT NULL,
    ora_inchidere  TIME     NOT NULL,
    CHECK (ora_deschidere < ora_inchidere),
    CHECK (extract(minute FROM ora_deschidere) IN (0, 30) AND extract(second FROM ora_deschidere) = 0),
    CHECK (extract(minute FROM ora_inchidere) IN (0, 30) AND extract(second FROM ora_inchidere) = 0),
    UNIQUE (resource_id, zi_saptamana, ora_deschidere)
);

CREATE TABLE maintenance_windows (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id  BIGINT      NOT NULL REFERENCES resources (id) ON DELETE CASCADE,
    created_by   BIGINT      NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    data_inceput TIMESTAMPTZ NOT NULL,
    data_sfarsit TIMESTAMPTZ NOT NULL,
    motiv        TEXT        NOT NULL,
    anulata_la   TIMESTAMPTZ,
    CHECK (data_inceput < data_sfarsit)
);
CREATE INDEX maintenance_resource_time_idx ON maintenance_windows (resource_id, data_inceput, data_sfarsit);

CREATE TABLE teams (
    id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nume VARCHAR(150) NOT NULL
);
CREATE UNIQUE INDEX teams_nume_unique ON teams (lower(nume));

CREATE TABLE reservations (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id          BIGINT             NOT NULL REFERENCES resources (id) ON DELETE RESTRICT,
    user_id              BIGINT             NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    team_id              BIGINT             NOT NULL REFERENCES teams (id) ON DELETE RESTRICT,
    decided_by           BIGINT             REFERENCES users (id) ON DELETE RESTRICT,
    data_inceput         TIMESTAMPTZ        NOT NULL,
    data_sfarsit         TIMESTAMPTZ        NOT NULL,
    scop                 TEXT,
    status               reservation_status NOT NULL DEFAULT 'PENDING',
    prima_rezervare      BOOLEAN            NOT NULL DEFAULT false,
    necesita_instruire   BOOLEAN            NOT NULL DEFAULT false,
    necesita_reanalizare BOOLEAN            NOT NULL DEFAULT false,
    motiv_respingere     TEXT,
    data_creare          TIMESTAMPTZ        NOT NULL DEFAULT now(),
    data_decizie         TIMESTAMPTZ,
    CHECK (data_inceput < data_sfarsit),
    -- Rezervările sunt formate din sloturi întregi de 30 de minute.
    CONSTRAINT reservation_slot_30_min CHECK (
        extract(epoch FROM data_inceput)::bigint % 1800 = 0
        AND extract(epoch FROM data_sfarsit)::bigint % 1800 = 0
    ),
    CONSTRAINT reservation_reject_reason CHECK (status <> 'REJECTED' OR motiv_respingere IS NOT NULL)
);
CREATE INDEX reservations_resource_time_idx ON reservations (resource_id, data_inceput, data_sfarsit);
CREATE INDEX reservations_user_idx ON reservations (user_id, status);
CREATE INDEX reservations_team_idx ON reservations (team_id);

CREATE TABLE resource_trainings (
    user_id         BIGINT      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    resource_id     BIGINT      NOT NULL REFERENCES resources (id) ON DELETE CASCADE,
    confirmed_by    BIGINT      NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    data_finalizare TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, resource_id)
);

CREATE TABLE waitlist_entries (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        BIGINT      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    resource_id    BIGINT      NOT NULL REFERENCES resources (id) ON DELETE CASCADE,
    data_inceput   TIMESTAMPTZ NOT NULL,
    data_sfarsit   TIMESTAMPTZ NOT NULL,
    data_inscriere TIMESTAMPTZ NOT NULL DEFAULT now(),
    notificat      BOOLEAN     NOT NULL DEFAULT false,
    CHECK (data_inceput < data_sfarsit),
    UNIQUE (user_id, resource_id, data_inceput, data_sfarsit)
);
CREATE INDEX waitlist_resource_time_idx ON waitlist_entries (resource_id, data_inceput, data_sfarsit);

CREATE TABLE notifications (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        BIGINT            NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    reservation_id BIGINT            REFERENCES reservations (id) ON DELETE SET NULL,
    tip            notification_type NOT NULL,
    mesaj          TEXT              NOT NULL,
    data_trimitere TIMESTAMPTZ
);
CREATE INDEX notifications_user_idx ON notifications (user_id);

-- Criteriul principal de succes: 0 suprapuneri peste capacitate (R10).
-- Verificarea se face pe fiecare slot de 30 de minute, deoarece două rezervări care nu se
-- suprapun între ele pot încăpea alături de una mai lungă. Blocarea rândului resursei
-- serializează cererile simultane pentru aceeași resursă.
CREATE FUNCTION check_reservation_capacity() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_max  SMALLINT;
    v_slot TIMESTAMPTZ;
BEGIN
    IF NEW.status NOT IN ('PENDING', 'AWAITING_TRAINING', 'APPROVED') THEN
        RETURN NEW;
    END IF;

    SELECT max_echipe_simultane INTO v_max
    FROM resources WHERE id = NEW.resource_id
    FOR UPDATE;

    SELECT slot INTO v_slot
    FROM generate_series(NEW.data_inceput, NEW.data_sfarsit - interval '30 minutes', interval '30 minutes') AS slot
    WHERE (
        SELECT count(*)
        FROM reservations r
        WHERE r.resource_id = NEW.resource_id
          AND r.id <> NEW.id
          AND r.status IN ('PENDING', 'AWAITING_TRAINING', 'APPROVED')
          AND r.data_inceput < slot + interval '30 minutes'
          AND r.data_sfarsit > slot
    ) >= v_max
    ORDER BY slot
    LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION 'Capacitatea resursei % este atinsă în slotul %', NEW.resource_id, v_slot
            USING ERRCODE = 'RR001';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER reservations_capacity
    BEFORE INSERT OR UPDATE OF status, data_inceput, data_sfarsit, resource_id ON reservations
    FOR EACH ROW EXECUTE FUNCTION check_reservation_capacity();

-- Două perioade active de mentenanță ale aceleiași resurse nu se pot suprapune.
CREATE FUNCTION check_maintenance_overlap() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.anulata_la IS NOT NULL THEN
        RETURN NEW;
    END IF;

    PERFORM 1 FROM resources WHERE id = NEW.resource_id FOR UPDATE;

    IF EXISTS (
        SELECT 1
        FROM maintenance_windows m
        WHERE m.resource_id = NEW.resource_id
          AND m.id <> NEW.id
          AND m.anulata_la IS NULL
          AND m.data_inceput < NEW.data_sfarsit
          AND m.data_sfarsit > NEW.data_inceput
    ) THEN
        RAISE EXCEPTION 'Intervalul se suprapune cu o altă mentenanță a resursei %', NEW.resource_id
            USING ERRCODE = 'RR002';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER maintenance_no_overlap
    BEFORE INSERT OR UPDATE ON maintenance_windows
    FOR EACH ROW EXECUTE FUNCTION check_maintenance_overlap();
