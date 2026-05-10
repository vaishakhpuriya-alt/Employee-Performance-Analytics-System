"""
models/analyzers.py
OOP layer: abstract base + concrete analyzers demonstrating
  – Abstraction   (ABC / abstract methods)
  – Inheritance   (BaseAnalyzer → PerformanceAnalyzer / SalaryAnalyzer)
  – Polymorphism  (each subclass implements generate_report() differently)
  – Encapsulation (private state, public interface)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from db import DatabaseConnection
from sql import queries
from processing import (
    row_iterator, filter_high_performers, filter_improving,
    map_salary_display, map_rating_stars, group_by,
    format_salary, format_rating, trend_arrow,
)
from utils import processing_logger, log_execution_time, DataNotFoundException


# ═══════════════════════════════════════════════════════════════════════════════
# Abstract base
# ═══════════════════════════════════════════════════════════════════════════════

class BaseAnalyzer(ABC):
    """
    Abstract base for all analytics components.
    Enforces a common interface and houses shared infrastructure.
    """

    def __init__(self, db: DatabaseConnection):
        self._db = db                          # encapsulated dependency
        self._results: list[dict] = []         # private cache

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def run(self) -> "BaseAnalyzer":
        """Execute queries and populate self._results. Returns self for chaining."""

    @abstractmethod
    def generate_report(self) -> str:
        """Format self._results into a human-readable report string."""

    # ── Shared helper ─────────────────────────────────────────────────────────

    def _require_results(self) -> None:
        if not self._results:
            raise DataNotFoundException("analyzer results", "run() not called or returned empty")

    @property
    def results(self) -> list[dict]:
        return list(self._results)            # return copy to protect encapsulation


# ═══════════════════════════════════════════════════════════════════════════════
# Salary Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class SalaryAnalyzer(BaseAnalyzer):
    """
    Analyses salary distribution using window functions (RANK, DENSE_RANK,
    ROW_NUMBER, running total, dept avg).
    """

    @log_execution_time(processing_logger)
    def run(self) -> "SalaryAnalyzer":
        rows = self._db.fetch_all(queries.SALARY_RANKING)
        self._results = list(row_iterator(rows))
        processing_logger.info("SalaryAnalyzer: loaded %d rows", len(self._results))
        return self

    def generate_report(self) -> str:       # Polymorphism: unique format
        self._require_results()
        lines = [
            "\n" + "═" * 110,
            " SALARY RANKING ANALYSIS — Window Functions (RANK / DENSE_RANK / ROW_NUMBER)",
            "═" * 110,
            f"{'#':>4}  {'Name':<20} {'Dept':<14} {'Salary':>12}  "
            f"{'RANK':>6} {'D_RANK':>7} {'ROW#':>5}  "
            f"{'Dept Avg':>12}  {'Running Σ':>14}",
            "─" * 110,
        ]
        for r in self._results:
            lines.append(
                f"{r['row_num_salary']:>4}.  {r['name']:<20} {r['department']:<14} "
                f"{format_salary(r['salary']):>12}  "
                f"{r['rank_salary']:>6} {r['dense_rank_salary']:>7} {r['row_num_salary']:>5}  "
                f"{format_salary(r['dept_avg_salary']):>12}  "
                f"{format_salary(r['running_total_salary']):>14}"
            )
        lines.append("═" * 110)
        return "\n".join(lines)

    def avg_comparison_report(self) -> str:
        """Extra polymorphic method: aggregate vs window avg comparison."""
        rows = self._db.fetch_all(queries.AVG_SALARY_COMPARISON)
        lines = [
            "\n" + "═" * 100,
            " AGGREGATE vs WINDOW AVG SALARY COMPARISON",
            "═" * 100,
            f"{'Name':<20} {'Dept':<14} {'Salary':>12}  {'Agg Avg':>12}  {'Win Avg':>12}  {'Δ from Avg':>12}",
            "─" * 100,
        ]
        for r in rows:
            delta = r["diff_from_avg"]
            arrow = "▲" if delta > 0 else "▼" if delta < 0 else "─"
            lines.append(
                f"{r['name']:<20} {r['department']:<14} "
                f"{format_salary(r['salary']):>12}  "
                f"{format_salary(r['agg_dept_avg']):>12}  "
                f"{format_salary(r['window_dept_avg']):>12}  "
                f"{arrow} {format_salary(abs(delta)):>10}"
            )
        lines.append("═" * 100)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Performance Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class PerformanceAnalyzer(BaseAnalyzer):
    """
    Tracks performance using LAG / LEAD window functions and
    filters for improving / top performers.
    """

    @log_execution_time(processing_logger)
    def run(self) -> "PerformanceAnalyzer":
        rows = self._db.fetch_all(queries.PERFORMANCE_TREND)
        self._results = list(map_rating_stars(row_iterator(rows)))
        processing_logger.info("PerformanceAnalyzer: loaded %d rows", len(self._results))
        return self

    def generate_report(self) -> str:       # Polymorphism: unique format
        self._require_results()
        lines = [
            "\n" + "═" * 95,
            " PERFORMANCE TREND ANALYSIS — LAG / LEAD Window Functions",
            "═" * 95,
            f"{'Name':<20} {'Dept':<14} {'Date':<12} {'Rating':>8}  {'Prev':>6}  {'Next':>6}  {'Δ':>4}  Stars",
            "─" * 95,
        ]
        for r in self._results:
            prev = str(r["prev_rating"]) if r["prev_rating"] is not None else " — "
            nxt  = str(r["next_rating"]) if r["next_rating"] is not None else " — "
            delta = r["rating_delta"]
            arrow = trend_arrow(delta)
            delta_str = f"{arrow}{abs(delta)}" if delta else " ─"
            lines.append(
                f"{r['name']:<20} {r['department']:<14} {r['review_date']:<12} "
                f"{r['rating']:>8}  {prev:>6}  {nxt:>6}  {delta_str:>4}  {r['stars']}"
            )
        lines.append("═" * 95)
        return "\n".join(lines)

    def top_performers_report(self) -> str:
        rows   = self._db.fetch_all(queries.TOP_PERFORMERS_PER_DEPT)
        top    = list(filter_high_performers(row_iterator(rows), threshold=4))
        lines  = [
            "\n" + "═" * 75,
            " TOP PERFORMERS PER DEPARTMENT (CTE + latest rating ≥ 4)",
            "═" * 75,
            f"{'Dept':<14} {'Name':<20} {'Salary':>12}  {'Rating':>8}  Stars",
            "─" * 75,
        ]
        for r in top:
            lines.append(
                f"{r['department']:<14} {r['name']:<20} "
                f"{format_salary(r['salary']):>12}  "
                f"{r['latest_rating']:>8}  {format_rating(r['latest_rating'])}"
            )
        if not top:
            lines.append("  (no top performers found)")
        lines.append("═" * 75)
        return "\n".join(lines)

    def improving_employees_report(self) -> str:
        improving = list(filter_improving(self._results))
        by_emp: dict[str, list] = {}
        for r in improving:
            by_emp.setdefault(r["name"], []).append(r)

        lines = [
            "\n" + "═" * 60,
            " EMPLOYEES WITH IMPROVING PERFORMANCE (rating_delta > 0)",
            "═" * 60,
        ]
        for name, records in sorted(by_emp.items()):
            lines.append(f"\n  {name} ({records[0]['department']})")
            for rec in records:
                lines.append(
                    f"    {rec['review_date']}  "
                    f"{rec['prev_rating']} → {rec['rating']}  ▲{rec['rating_delta']}"
                )
        lines.append("\n" + "═" * 60)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Hierarchy Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class HierarchyAnalyzer(BaseAnalyzer):
    """Builds the org-chart using a Recursive CTE."""

    @log_execution_time(processing_logger)
    def run(self) -> "HierarchyAnalyzer":
        rows = self._db.fetch_all(queries.EMPLOYEE_HIERARCHY)
        self._results = list(row_iterator(rows))
        processing_logger.info("HierarchyAnalyzer: %d nodes loaded", len(self._results))
        return self

    def generate_report(self) -> str:
        self._require_results()
        lines = [
            "\n" + "═" * 65,
            " EMPLOYEE HIERARCHY TREE — Recursive CTE",
            "═" * 65,
        ]
        for r in self._results:
            lines.append(f"  {r['hierarchy_display']}  [{r['department']}]")
        lines.append("═" * 65)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Attendance Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class AttendanceAnalyzer(BaseAnalyzer):
    """Summarises attendance and flags frequent absentees."""

    @log_execution_time(processing_logger)
    def run(self) -> "AttendanceAnalyzer":
        rows = self._db.fetch_all(queries.ATTENDANCE_SUMMARY)
        self._results = list(row_iterator(rows))
        processing_logger.info("AttendanceAnalyzer: %d records loaded", len(self._results))
        return self

    def generate_report(self) -> str:
        self._require_results()
        lines = [
            "\n" + "═" * 80,
            " ATTENDANCE SUMMARY",
            "═" * 80,
            f"{'Name':<20} {'Dept':<14} {'Present':>8} {'Absent':>7} {'Leave':>6}  {'Att%':>6}  Bar",
            "─" * 80,
        ]
        for r in self._results:
            bar_len = int(r["attendance_pct"] / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(
                f"{r['name']:<20} {r['department']:<14} "
                f"{r['present_days']:>8} {r['absent_days']:>7} {r['leave_days']:>6}  "
                f"{r['attendance_pct']:>5.1f}%  {bar}"
            )
        lines.append("═" * 80)
        return "\n".join(lines)