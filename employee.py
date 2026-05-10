"""
models/employee.py
Domain model for an Employee with encapsulated salary and derived properties.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Employee:
    """
    Represents a single employee record.

    Salary is a private-by-convention attribute (_salary);
    exposed through a property so we can add validation later.
    """

    employee_id: int
    name: str
    department: str
    _salary: float = field(repr=False)
    joining_date: str
    manager_id: int | None = None

    # ── Constructors ─────────────────────────────────────────────────────────

    @classmethod
    def from_row(cls, row) -> "Employee":
        """Build an Employee from a sqlite3.Row / dict-like object."""
        return cls(
            employee_id=row["employee_id"],
            name=row["name"],
            department=row["department"],
            _salary=row["salary"],
            joining_date=row["joining_date"],
            manager_id=row["manager_id"] if "manager_id" in row.keys() else None,
        )

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def salary(self) -> float:
        return self._salary

    @salary.setter
    def salary(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"Salary cannot be negative: {value}")
        self._salary = value

    @property
    def tenure_years(self) -> float:
        """Years since joining (approximate)."""
        joined = date.fromisoformat(self.joining_date)
        delta = date.today() - joined
        return round(delta.days / 365.25, 1)

    # ── Dunder helpers ────────────────────────────────────────────────────────

    def __str__(self) -> str:
        return (
            f"Employee({self.employee_id}, {self.name!r}, "
            f"dept={self.department!r}, salary={self._salary:,.0f}, "
            f"tenure={self.tenure_years}y)"
        )

    def __repr__(self) -> str:
        return self.__str__()