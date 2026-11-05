"""Generează diagrama ERD (erd.svg) pentru Research Resource Manager.

Rulare: python3 docs/db/generate_erd.py
Tabelele și coloanele trebuie păstrate în acord cu db/schema.sql.
"""
from html import escape
from pathlib import Path

WIDTH, HEIGHT = 1640, 1250
ROW, HEADER, BOX_W = 20, 30, 300

# nume: (x, y, coloane). Marcaje coloană: PK, FK sau PK,FK.
TABLES = {
    "resource_categories": (40, 40, [("id", "BIGINT", "PK"), ("nume", "VARCHAR(100)", "UQ"), ("descriere", "TEXT", "")]),
    "resources": (40, 240, [
        ("id", "BIGINT", "PK"), ("category_id", "BIGINT", "FK"), ("tip", "resource_type", ""),
        ("nume", "VARCHAR(150)", ""), ("descriere", "TEXT", ""), ("locatie", "VARCHAR(150)", ""),
        ("etaj", "SMALLINT", ""), ("locuri", "INTEGER", ""), ("echipare", "TEXT", ""), ("model", "VARCHAR(150)", ""),
        ("max_echipe_simultane", "SMALLINT", ""), ("durata_maxima_min", "INTEGER", ""),
        ("necesita_instruire", "BOOLEAN", ""), ("status", "resource_status", ""), ("data_creare", "TIMESTAMPTZ", ""),
    ]),
    "operating_schedules": (40, 640, [
        ("id", "BIGINT", "PK"), ("resource_id", "BIGINT", "FK"), ("zi_saptamana", "SMALLINT", ""),
        ("ora_deschidere", "TIME", ""), ("ora_inchidere", "TIME", ""),
    ]),
    "maintenance_windows": (40, 830, [
        ("id", "BIGINT", "PK"), ("resource_id", "BIGINT", "FK"), ("created_by", "BIGINT", "FK"),
        ("data_inceput", "TIMESTAMPTZ", ""), ("data_sfarsit", "TIMESTAMPTZ", ""), ("motiv", "TEXT", ""),
        ("anulata_la", "TIMESTAMPTZ", ""),
    ]),
    "reservations": (480, 240, [
        ("id", "BIGINT", "PK"), ("resource_id", "BIGINT", "FK"), ("user_id", "BIGINT", "FK"),
        ("team_id", "BIGINT", "FK"), ("decided_by", "BIGINT", "FK"), ("data_inceput", "TIMESTAMPTZ", ""),
        ("data_sfarsit", "TIMESTAMPTZ", ""), ("scop", "TEXT", ""), ("status", "reservation_status", ""),
        ("prima_rezervare", "BOOLEAN", ""), ("necesita_instruire", "BOOLEAN", ""),
        ("necesita_reanalizare", "BOOLEAN", ""), ("motiv_respingere", "TEXT", ""),
        ("data_creare", "TIMESTAMPTZ", ""), ("data_decizie", "TIMESTAMPTZ", ""),
    ]),
    "teams": (480, 40, [("id", "BIGINT", "PK"), ("nume", "VARCHAR(150)", "UQ")]),
    "resource_admins": (480, 640, [("resource_id", "BIGINT", "PK,FK"), ("user_id", "BIGINT", "PK,FK")]),
    "resource_trainings": (480, 790, [
        ("user_id", "BIGINT", "PK,FK"), ("resource_id", "BIGINT", "PK,FK"), ("confirmed_by", "BIGINT", "FK"),
        ("data_finalizare", "TIMESTAMPTZ", ""),
    ]),
    "waitlist_entries": (480, 980, [
        ("id", "BIGINT", "PK"), ("user_id", "BIGINT", "FK"), ("resource_id", "BIGINT", "FK"),
        ("data_inceput", "TIMESTAMPTZ", ""), ("data_sfarsit", "TIMESTAMPTZ", ""),
        ("data_inscriere", "TIMESTAMPTZ", ""), ("notificat", "BOOLEAN", ""),
    ]),
    "users": (920, 190, [
        ("id", "BIGINT", "PK"), ("google_sub", "VARCHAR(255)", "UQ"), ("email", "VARCHAR(320)", "UQ"),
        ("nume", "VARCHAR(100)", ""), ("prenume", "VARCHAR(100)", ""), ("role", "user_role", ""),
        ("data_creare", "TIMESTAMPTZ", ""),
    ]),
    "notifications": (920, 640, [
        ("id", "BIGINT", "PK"), ("user_id", "BIGINT", "FK"), ("reservation_id", "BIGINT", "FK"),
        ("tip", "notification_type", ""), ("mesaj", "TEXT", ""), ("data_trimitere", "TIMESTAMPTZ", ""),
    ]),
}

ENUMS = {
    "user_role": ["STUDENT", "CADRU_DIDACTIC", "CERCETATOR", "ADMIN"],
    "resource_type": ["SALA", "ECHIPAMENT"],
    "resource_status": ["ACTIVE", "MAINTENANCE", "INACTIVE"],
    "reservation_status": ["PENDING", "AWAITING_TRAINING", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED"],
    "notification_type": ["CERERE_NOUA", "APROBARE", "RESPINGERE", "ANULARE", "INSTRUIRE", "MENTENANTA", "LISTA_ASTEPTARE"],
}

# (tabel cu FK, coloană, tabel referit, puncte intermediare pe traseu ortogonal)
# Traseele folosesc culoarele dintre coloanele de tabele. y: None = rândul FK, "ref" = rândul PK.
RELATIONS = [
    ("resources", "category_id", "resource_categories", "left", [(28, None), (28, "ref")]),
    ("operating_schedules", "resource_id", "resources", "left", [(18, None), (18, "ref")]),
    ("maintenance_windows", "resource_id", "resources", "left", [(8, None), (8, "ref")]),
    ("reservations", "resource_id", "resources", "right", [(400, None), (400, "ref")]),
    ("reservations", "team_id", "teams", "right", [(420, None), (420, "ref")]),
    ("resource_admins", "resource_id", "resources", "right", [(380, None), (380, "ref")]),
    ("resource_trainings", "resource_id", "resources", "right", [(370, None), (370, "ref")]),
    ("waitlist_entries", "resource_id", "resources", "right", [(360, None), (360, "ref")]),
    ("reservations", "user_id", "users", "left", [(840, None), (840, "ref")]),
    ("reservations", "decided_by", "users", "left", [(860, None), (860, "ref")]),
    ("resource_admins", "user_id", "users", "left", [(820, None), (820, "ref")]),
    ("resource_trainings", "user_id", "users", "left", [(830, None), (830, "ref")]),
    ("resource_trainings", "confirmed_by", "users", "left", [(850, None), (850, "ref")]),
    ("waitlist_entries", "user_id", "users", "left", [(870, None), (870, "ref")]),
    ("notifications", "user_id", "users", "left", [(880, None), (880, "ref")]),
    ("notifications", "reservation_id", "reservations", "right", [(890, None), (890, "ref")]),
    ("maintenance_windows", "created_by", "users", "left", [(350, None), (350, 1190), (900, 1190), (900, "ref")]),
]


def row_y(table, column=None):
    x, y, columns = TABLES[table]
    if column is None:
        return y + HEADER + ROW // 2
    index = [c[0] for c in columns].index(column)
    return y + HEADER + ROW * index + ROW // 2


def side_x(table, lane_x):
    x, _, _ = TABLES[table]
    return x if lane_x < x else x + BOX_W


def relation(source, column, target, _side, lanes):
    lane = lanes[0][0]
    start = (side_x(source, lane), row_y(source, column))
    end = (side_x(target, lanes[-1][0]), row_y(target))
    middle = [(x, start[1] if y is None else end[1] if y == "ref" else y) for x, y in lanes]
    points = [start, *middle, end]
    path = " ".join(f"{x},{y}" for x, y in points)
    # Picior de cioară la „mulți” (FK), bară la „unu” (PK).
    sign = 1 if lane > start[0] else -1
    crow = (
        f'<path class="rel" d="M{start[0] + sign * 10},{start[1]} L{start[0]},{start[1] - 5} '
        f'M{start[0] + sign * 10},{start[1]} L{start[0]},{start[1] + 5}"/>'
    )
    end_sign = 1 if lanes[-1][0] > end[0] else -1
    bar = f'<path class="rel" d="M{end[0] + end_sign * 7},{end[1] - 5} V{end[1] + 5}"/>'
    return f'<polyline class="rel" points="{path}"/>{crow}{bar}'


def table_svg(name):
    x, y, columns = TABLES[name]
    height = HEADER + ROW * len(columns)
    parts = [
        f'<rect class="box" x="{x}" y="{y}" width="{BOX_W}" height="{height}" rx="4"/>',
        f'<path class="head" d="M{x},{y + HEADER} V{y + 4} Q{x},{y} {x + 4},{y} H{x + BOX_W - 4} '
        f'Q{x + BOX_W},{y} {x + BOX_W},{y + 4} V{y + HEADER} Z"/>',
        f'<text class="title" x="{x + 10}" y="{y + 20}">{name}</text>',
    ]
    for index, (column, sql_type, mark) in enumerate(columns):
        row = y + HEADER + ROW * index
        baseline = row + 14
        if index % 2:
            parts.append(f'<rect class="zebra" x="{x + 1}" y="{row}" width="{BOX_W - 2}" height="{ROW}"/>')
        parts.append(f'<text class="mark" x="{x + 8}" y="{baseline}">{mark}</text>')
        parts.append(f'<text class="col" x="{x + 48}" y="{baseline}">{escape(column)}</text>')
        parts.append(f'<text class="type" x="{x + BOX_W - 8}" y="{baseline}" text-anchor="end">{escape(sql_type)}</text>')
    return "".join(parts)


def enums_svg():
    x, y = 1290, 240
    parts = [f'<text class="title dark" x="{x}" y="{y - 12}">Tipuri enumerate</text>']
    for name, values in ENUMS.items():
        height = HEADER + 18 * len(values) + 6
        parts.append(f'<rect class="box" x="{x}" y="{y}" width="310" height="{height}" rx="4"/>')
        parts.append(f'<rect class="enumhead" x="{x}" y="{y}" width="310" height="{HEADER}" rx="4"/>')
        parts.append(f'<text class="title" x="{x + 10}" y="{y + 20}">{name}</text>')
        for index, value in enumerate(values):
            parts.append(f'<text class="col" x="{x + 12}" y="{y + HEADER + 16 + 18 * index}">{value}</text>')
        y += height + 16
    return "".join(parts)


STYLE = """
text { font-family: Helvetica, Arial, sans-serif; font-size: 13px; }
.bg { fill: #ffffff; }
.box { fill: #ffffff; stroke: #5b6b7f; stroke-width: 1.2; }
.head { fill: #2f5d8a; }
.enumhead { fill: #7a5a2f; }
.zebra { fill: #f3f6f9; }
.title { fill: #ffffff; font-weight: 700; font-size: 14px; }
.title.dark { fill: #1c2733; }
.heading { fill: #1c2733; font-weight: 700; font-size: 22px; }
.note { fill: #4a5866; font-size: 13px; }
.col { fill: #1c2733; }
.type { fill: #5b6b7f; font-size: 12px; }
.mark { fill: #a3361f; font-size: 10px; font-weight: 700; }
.rel { fill: none; stroke: #5b6b7f; stroke-width: 1.2; }
"""


def main():
    body = [f'<rect class="bg" width="{WIDTH}" height="{HEIGHT}"/>']
    body.append('<text class="heading" x="920" y="62">RRM - Diagrama Entitate-Relație (PostgreSQL)</text>')
    body.append('<text class="note" x="920" y="88">PK cheie primară · FK cheie străină · UQ valoare unică</text>')
    body.append('<text class="note" x="920" y="108">Bara marchează capătul „unu”, piciorul de cioară capătul „mulți”.</text>')
    body.extend(relation(*item) for item in RELATIONS)
    body.extend(table_svg(name) for name in TABLES)
    body.append(enums_svg())
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
        f"<style>{STYLE}</style>{''.join(body)}</svg>"
    )
    Path(__file__).with_name("erd.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
