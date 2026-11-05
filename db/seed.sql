-- Date de test pentru demonstrație. Resursele și persoanele provin din prototipul Figma.

INSERT INTO users (google_sub, email, nume, prenume, role) VALUES
    ('seed-admin-maria',   'maria.ionescu@example.ro',            'Ionescu',    'Maria',  'ADMIN'),
    ('seed-admin-popescu', 'a.popescu@example.ro',                'Popescu',    'Alexandru', 'ADMIN'),
    ('seed-andrei',        'andrei.popescu@student.example.ro',   'Popescu',    'Andrei', 'STUDENT'),
    ('seed-dan',           'dan.constantin@example.ro',           'Constantin', 'Dan',    'CERCETATOR'),
    ('seed-elena',         'elena.vasile@example.ro',             'Vasile',     'Elena',  'CADRU_DIDACTIC'),
    ('seed-radu',          'radu.tudor@student.example.ro',       'Tudor',      'Radu',   'STUDENT');

INSERT INTO resource_categories (nume, descriere) VALUES
    ('Săli și laboratoare',  'Săli de seminar, conferințe, studiu și laboratoare'),
    ('Imprimante 3D',        'Echipamente de fabricare aditivă'),
    ('Roboți',               'Roboți industriali și colaborativi'),
    ('Imprimante',           'Imprimante clasice'),
    ('Aparate de măsurare',  'Aparate de măsură și analiză');

INSERT INTO resources (category_id, tip, nume, descriere, locatie, etaj, locuri, echipare, model,
                       max_echipe_simultane, durata_maxima_min, necesita_instruire)
SELECT c.id, v.tip::resource_type, v.nume, v.descriere, v.locatie, v.etaj, v.locuri, v.echipare, v.model,
       v.max_echipe, v.durata, v.instruire
FROM (VALUES
    ('Săli și laboratoare', 'SALA', 'D205', 'Sală de seminar',       'D205', 2, 24, 'Proiector',                   NULL,   2, NULL, false),
    ('Săli și laboratoare', 'SALA', 'C202', 'Laborator robotică',    'C202', 2, 16, 'Proiector, tablă interactivă', NULL,  2, NULL, false),
    ('Săli și laboratoare', 'SALA', 'C102', 'Laborator electronică', 'C102', 1, 20, 'Stații de lucru',             NULL,   1, NULL, false),
    ('Săli și laboratoare', 'SALA', 'B110', 'Sală de conferințe',    'B110', 1, 60, 'Proiector, sistem audio',     NULL,   1, NULL, false),
    ('Săli și laboratoare', 'SALA', 'B204', 'Sală de studiu',        'B204', 2, 12, NULL,                          NULL,   2, NULL, false),
    ('Imprimante 3D',       'ECHIPAMENT', 'Imprimantă 3D',        'Fabricare aditivă', 'C202', 2, NULL, NULL, NULL,   1, 240,  true),
    ('Roboți',              'ECHIPAMENT', 'Robot colaborativ',    'Robotică',          'C202', 2, NULL, NULL, 'UR5e', 1, 120,  true),
    ('Aparate de măsurare', 'ECHIPAMENT', 'Osciloscop',           'Electronică',       'C102', 1, NULL, NULL, NULL,   1, NULL, false),
    ('Aparate de măsurare', 'ECHIPAMENT', 'Microscop electronic', 'Analiză materiale', 'B104', 1, NULL, NULL, NULL,   1, 240,  true),
    ('Aparate de măsurare', 'ECHIPAMENT', 'Spectrometru FTIR',    'Chimie analitică',  'B110', 1, NULL, NULL, NULL,   1, 240,  true)
) AS v(categorie, tip, nume, descriere, locatie, etaj, locuri, echipare, model, max_echipe, durata, instruire)
JOIN resource_categories c ON c.nume = v.categorie;

-- Maria administrează sălile, Alexandru echipamentele.
INSERT INTO resource_admins (resource_id, user_id)
SELECT r.id, u.id
FROM resources r
JOIN users u ON u.email = CASE r.tip WHEN 'SALA' THEN 'maria.ionescu@example.ro' ELSE 'a.popescu@example.ro' END;

-- Luni – Vineri, 08:00 – 22:00, ca în prototip.
INSERT INTO operating_schedules (resource_id, zi_saptamana, ora_deschidere, ora_inchidere)
SELECT r.id, zi, '08:00', '22:00'
FROM resources r
CROSS JOIN generate_series(1, 5) AS zi;

INSERT INTO teams (nume) VALUES ('Echipa Robotică'), ('Echipa Materiale'), ('Echipa Electronică');

INSERT INTO reservations (resource_id, user_id, team_id, decided_by, data_inceput, data_sfarsit, scop,
                          status, prima_rezervare, necesita_instruire, motiv_respingere, data_decizie)
SELECT r.id, u.id, t.id, a.id, v.inceput::timestamptz, v.sfarsit::timestamptz, v.scop,
       v.status::reservation_status, v.prima, v.instruire, v.motiv,
       CASE WHEN a.id IS NOT NULL THEN TIMESTAMPTZ '2026-11-05 10:00+02' END
FROM (VALUES
    ('C202',              'andrei.popescu@student.example.ro', 'Echipa Robotică',    'maria.ionescu@example.ro', '2026-11-12 12:00+02', '2026-11-12 14:00+02', 'Testare braț robotic',   'APPROVED', true,  false, NULL),
    ('Imprimantă 3D',     'andrei.popescu@student.example.ro', 'Echipa Robotică',    NULL,                       '2026-11-13 08:00+02', '2026-11-13 10:00+02', 'Printare piese',         'PENDING',  true,  false, NULL),
    ('Robot colaborativ', 'elena.vasile@example.ro',           'Echipa Robotică',    'a.popescu@example.ro',     '2026-11-16 18:00+02', '2026-11-16 20:00+02', 'Experiment colaborativ', 'APPROVED', false, false, NULL),
    ('D205',              'radu.tudor@student.example.ro',     'Echipa Electronică', 'maria.ionescu@example.ro', '2026-11-10 10:00+02', '2026-11-10 12:00+02', 'Seminar',                'REJECTED', false, false, 'Sala este rezervată pentru examen.'),
    ('Osciloscop',        'andrei.popescu@student.example.ro', 'Echipa Electronică', 'a.popescu@example.ro',     '2026-11-17 14:00+02', '2026-11-17 16:00+02', 'Măsurători',             'APPROVED', false, false, NULL),
    ('B110',              'andrei.popescu@student.example.ro', 'Echipa Robotică',    NULL,                       '2026-11-18 09:00+02', '2026-11-18 11:00+02', 'Prezentare proiect',     'PENDING',  true,  false, NULL),
    ('Microscop electronic', 'dan.constantin@example.ro',      'Echipa Materiale',   NULL,                       '2026-11-19 12:00+02', '2026-11-19 14:00+02', 'Analiză probe',          'AWAITING_TRAINING', true, true, NULL),
    ('Spectrometru FTIR', 'dan.constantin@example.ro',         'Echipa Materiale',   NULL,                       '2026-11-20 08:00+02', '2026-11-20 10:00+02', 'Analiză spectru',        'PENDING',  true,  false, NULL)
) AS v(resursa, solicitant, echipa, admin, inceput, sfarsit, scop, status, prima, instruire, motiv)
JOIN resources r ON r.nume = v.resursa
JOIN users u ON u.email = v.solicitant
JOIN teams t ON t.nume = v.echipa
LEFT JOIN users a ON a.email = v.admin;

INSERT INTO resource_trainings (user_id, resource_id, confirmed_by)
SELECT u.id, r.id, a.id
FROM users u, resources r, users a
WHERE u.email = 'elena.vasile@example.ro' AND r.nume = 'Robot colaborativ' AND a.email = 'a.popescu@example.ro';

INSERT INTO maintenance_windows (resource_id, created_by, data_inceput, data_sfarsit, motiv)
SELECT r.id, a.id, '2026-11-23 08:00+02', '2026-11-23 18:00+02', 'Calibrare anuală'
FROM resources r, users a
WHERE r.nume = 'Spectrometru FTIR' AND a.email = 'a.popescu@example.ro';

INSERT INTO waitlist_entries (user_id, resource_id, data_inceput, data_sfarsit)
SELECT u.id, r.id, '2026-11-17 14:00+02', '2026-11-17 16:00+02'
FROM users u, resources r
WHERE u.email = 'radu.tudor@student.example.ro' AND r.nume = 'Osciloscop';

INSERT INTO notifications (user_id, reservation_id, tip, mesaj, data_trimitere)
SELECT res.user_id, res.id, 'APROBARE', 'Rezervarea ta a fost aprobată.', TIMESTAMPTZ '2026-11-05 10:00+02'
FROM reservations res
WHERE res.status = 'APPROVED';
