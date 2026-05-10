"""
main.py
Orchestrates the HR Analytics System end-to-end:
  1. Seed the SQLite database
  2. Run all analyzers
  3. Print formatted reports
  4. Demonstrate generator / iterator streaming
  5. Demonstrate functional pipeline
"""

import sys
import os

# ── Make project root importable ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from db import DatabaseConnection
from db.seed import seed_database
from models import (
    Employee,
    SalaryAnalyzer,
    PerformanceAnalyzer,
    HierarchyAnalyzer,
    AttendanceAnalyzer,
)
from processing import (
    row_iterator, chunked, group_by, pipeline,
    filter_department, map_salary_display, format_salary,
)
from sql import queries
from utils import processing_logger, db_logger, DataNotFoundException, QueryExecutionError


# ═══════════════════════════════════════════════════════════════════════════════
# Section printers
# ═══════════════════════════════════════════════════════════════════════════════

def section(title: str) -> None:
    print(f"\n\n{'━' * 80}")
    print(f"  {title}")
    print(f"{'━' * 80}")


# ═══════════════════════════════════════════════════════════════════════════════
# Demonstrate generator / iterator streaming
# ═══════════════════════════════════════════════════════════════════════════════

def demo_generator_streaming(db: DatabaseConnection) -> None:
    section("GENERATOR STREAMING — processing employees in chunks of 4")
    print("  (Using db.stream_rows() + chunked() generator)")

    stream = db.stream_rows("SELECT employee_id, name, department, salary, joining_date, manager_id FROM employees")
    for i, chunk in enumerate(chunked(stream, size=4), start=1):
        print(f"\n  Chunk {i}:")
        for row in chunk:
            emp = Employee.from_row(row)
            print(f"    {emp}")


# ═══════════════════════════════════════════════════════════════════════════════
# Demonstrate functional pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def demo_functional_pipeline(db: DatabaseConnection) -> None:
    section("FUNCTIONAL PIPELINE — Engineering dept salary display")

    rows = db.fetch_all("SELECT * FROM employees")

    # pipeline: row_iterator → filter dept → map salary display
    process = pipeline(
        list,                                        # materialise generator
        lambda rs: filter_department(rs, "Engineering"),
        lambda rs: map_salary_display(rs),
        list,
    )
    results = process(row_iterator(rows))

    print(f"\n  {'Name':<20} {'Salary':>14}")
    print("  " + "─" * 36)
    for r in results:
        print(f"  {r['name']:<20} {r['salary_display']:>14}")


# ═══════════════════════════════════════════════════════════════════════════════
# Demonstrate group_by aggregation
# ═══════════════════════════════════════════════════════════════════════════════

def demo_group_by(db: DatabaseConnection) -> None:
    section("GROUP_BY — Average salary per department (Python-side aggregation)")

    rows   = db.fetch_all("SELECT department, salary FROM employees")
    groups = group_by(row_iterator(rows), key="department")

    print(f"\n  {'Department':<16} {'Avg Salary':>14}  {'Head Count':>10}")
    print("  " + "─" * 44)
    for dept, members in sorted(groups.items()):
        avg = sum(m["salary"] for m in members) / len(members)
        print(f"  {dept:<16} {format_salary(avg):>14}  {len(members):>10}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("\n" + "█" * 80)
    print("  HR ANALYTICS SYSTEM  —  Python + SQL + OOP + Functional Programming")
    print("█" * 80)

    try:
        with DatabaseConnection("hr_analytics.db") as db:

            # ── 1. Seed ───────────────────────────────────────────────────────
            section("DATABASE SEEDING")
            seed_database(db)
            print("  ✔ Database seeded successfully.")

            # ── 2. Salary analysis ────────────────────────────────────────────
            salary_az = SalaryAnalyzer(db).run()
            print(salary_az.generate_report())
            print(salary_az.avg_comparison_report())

            # ── 3. Performance analysis ───────────────────────────────────────
            perf_az = PerformanceAnalyzer(db).run()
            print(perf_az.generate_report())
            print(perf_az.top_performers_report())
            print(perf_az.improving_employees_report())

            # ── 4. Hierarchy (Recursive CTE) ──────────────────────────────────
            hier_az = HierarchyAnalyzer(db).run()
            print(hier_az.generate_report())

            # ── 5. Attendance ─────────────────────────────────────────────────
            att_az = AttendanceAnalyzer(db).run()
            print(att_az.generate_report())

            # ── 6. Generator streaming demo ───────────────────────────────────
            demo_generator_streaming(db)

            # ── 7. Functional pipeline demo ───────────────────────────────────
            demo_functional_pipeline(db)

            # ── 8. Group-by aggregation demo ──────────────────────────────────
            demo_group_by(db)

            # ── 9. Custom exception demo ──────────────────────────────────────
            section("CUSTOM EXCEPTION DEMO")
            try:
                rows = db.fetch_all("SELECT * FROM employees WHERE department = 'Narnia'")
                if not rows:
                    raise DataNotFoundException("employees", "department = 'Narnia'")
            except DataNotFoundException as exc:
                processing_logger.warning("Caught expected exception: %s", exc)
                print(f"\n  ⚠  DataNotFoundException caught: {exc}")

    except QueryExecutionError as exc:
        db_logger.error("Fatal query error: %s", exc)
        print(f"\n  ✖  QueryExecutionError: {exc}")
        sys.exit(1)
    except Exception as exc:
        db_logger.error("Unexpected error: %s", exc, exc_info=True)
        print(f"\n  ✖  Unexpected error: {exc}")
        sys.exit(1)
    else:
        processing_logger.info("All analytics completed successfully.")
        print("\n\n" + "█" * 80)
        print("  ✔ All analytics completed. Logs written to logs/db.log and logs/processing.log")
        print("█" * 80 + "\n")
    finally:
        db_logger.info("Main execution finished.")


if __name__ == "__main__":
    main()