"""
db/seed.py
Creates and populates the three core tables plus a manager-hierarchy table
used by the recursive CTE example.
"""

from db.connection import DatabaseConnection
from utils import db_logger

# ─── DDL ──────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    employee_id   INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    department    TEXT    NOT NULL,
    salary        REAL    NOT NULL,
    joining_date  TEXT    NOT NULL,
    manager_id    INTEGER REFERENCES employees(employee_id)
);

CREATE TABLE IF NOT EXISTS performance (
    review_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL REFERENCES employees(employee_id),
    review_date   TEXT    NOT NULL,
    rating        INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL REFERENCES employees(employee_id),
    date          TEXT    NOT NULL,
    status        TEXT    NOT NULL CHECK(status IN ('Present','Absent','Leave'))
);
"""

# ─── Seed data ─────────────────────────────────────────────────────────────────

EMPLOYEES = [
    # (id, name, dept, salary, joining_date, manager_id)
    (1,  "Alice Johnson",  "Engineering",  95000, "2019-03-15", None),
    (2,  "Bob Smith",      "Engineering",  88000, "2020-06-01", 1),
    (3,  "Carol White",    "Engineering",  72000, "2021-09-10", 1),
    (4,  "David Brown",    "Marketing",    82000, "2018-11-20", None),
    (5,  "Eve Davis",      "Marketing",    76000, "2020-02-14", 4),
    (6,  "Frank Miller",   "Marketing",    68000, "2022-01-05", 4),
    (7,  "Grace Wilson",   "HR",           65000, "2019-07-22", None),
    (8,  "Hank Moore",     "HR",           61000, "2021-04-18", 7),
    (9,  "Ivy Taylor",     "Engineering",  91000, "2017-12-01", 1),
    (10, "Jack Anderson",  "Marketing",    79000, "2019-08-30", 4),
    (11, "Karen Thomas",   "HR",           63000, "2020-11-11", 7),
    (12, "Leo Jackson",    "Engineering",  85000, "2018-05-25", 1),
]

PERFORMANCE = [
    # (employee_id, review_date, rating)
    (1, "2022-06-30", 5), (1, "2023-06-30", 5), (1, "2024-06-30", 4),
    (2, "2022-06-30", 3), (2, "2023-06-30", 4), (2, "2024-06-30", 5),
    (3, "2022-06-30", 4), (3, "2023-06-30", 3), (3, "2024-06-30", 4),
    (4, "2022-06-30", 5), (4, "2023-06-30", 5), (4, "2024-06-30", 5),
    (5, "2022-06-30", 2), (5, "2023-06-30", 3), (5, "2024-06-30", 4),
    (6, "2022-06-30", 3), (6, "2023-06-30", 3), (6, "2024-06-30", 2),
    (7, "2022-06-30", 4), (7, "2023-06-30", 4), (7, "2024-06-30", 5),
    (8, "2022-06-30", 3), (8, "2023-06-30", 2), (8, "2024-06-30", 3),
    (9, "2022-06-30", 5), (9, "2023-06-30", 4), (9, "2024-06-30", 5),
   (10, "2022-06-30", 4), (10, "2023-06-30", 5), (10, "2024-06-30", 4),
   (11, "2022-06-30", 2), (11, "2023-06-30", 3), (11, "2024-06-30", 3),
   (12, "2022-06-30", 4), (12, "2023-06-30", 4), (12, "2024-06-30", 5),
]

ATTENDANCE = [
    # Simulate 3 months for each employee
    *[
        (emp_id, f"2024-{month:02d}-{day:02d}", status)
        for emp_id in range(1, 13)
        for month in [1, 2, 3]
        for day, status in [
            (5,  "Present"), (8,  "Present"), (9,  "Present"),
            (10, "Leave"),   (12, "Present"), (15, "Absent"),
            (16, "Present"), (17, "Present"), (19, "Present"),
            (22, "Present"), (23, "Present"), (24, "Present"),
        ]
    ]
]


def seed_database(db: DatabaseConnection) -> None:
    """Drop existing tables and re-seed with fresh data."""
    db_logger.info("Seeding database…")

    # Drop + recreate
    for tbl in ("attendance", "performance", "employees"):
        db.execute(f"DROP TABLE IF EXISTS {tbl}")

    for stmt in SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            db.execute(stmt)

    db.execute_many(
        "INSERT INTO employees VALUES (?,?,?,?,?,?)", EMPLOYEES
    )
    db.execute_many(
        "INSERT INTO performance(employee_id, review_date, rating) VALUES (?,?,?)",
        PERFORMANCE,
    )
    db.execute_many(
        "INSERT INTO attendance(employee_id, date, status) VALUES (?,?,?)",
        ATTENDANCE,
    )
    db_logger.info(
        "Seeded %d employees, %d performance records, %d attendance records",
        len(EMPLOYEES), len(PERFORMANCE), len(ATTENDANCE),
    )