"""
processing/transformations.py
Pure functional helpers using map(), filter(), lambda, and higher-order functions.
All functions accept iterables and return iterators/generators for memory efficiency.
"""

from __future__ import annotations
from typing import Callable, Iterable, Any, Iterator

from utils import processing_logger, log_execution_time


# ─── Lambdas / pure transforms ─────────────────────────────────────────────────

format_salary   = lambda v: f"${v:>10,.2f}"
format_rating   = lambda r: "★" * int(r) + "☆" * (5 - int(r))
pct_label       = lambda p: f"{p:.1f}%"
dept_label      = lambda d: d.upper().center(14)
trend_arrow     = lambda delta: ("▲" if delta and delta > 0
                                 else "▼" if delta and delta < 0
                                 else "─")


# ─── map() wrappers ────────────────────────────────────────────────────────────

def map_salary_display(rows) -> Iterator[dict]:
    """Yield each row enriched with a formatted salary string."""
    return map(
        lambda r: {**dict(r), "salary_display": format_salary(r["salary"])},
        rows
    )


def map_rating_stars(rows) -> Iterator[dict]:
    """Yield each row enriched with a star-string rating."""
    return map(
        lambda r: {**dict(r), "stars": format_rating(r["rating"])},
        rows
    )


# ─── filter() wrappers ─────────────────────────────────────────────────────────

def filter_high_performers(rows, threshold: int = 4) -> filter:
    """Keep only rows where latest_rating >= threshold."""
    return filter(lambda r: r["latest_rating"] >= threshold, rows)


def filter_improving(rows) -> filter:
    """Keep only rows where rating_delta > 0 (performance is improving)."""
    return filter(lambda r: r["rating_delta"] is not None and r["rating_delta"] > 0, rows)


def filter_department(rows, dept: str) -> filter:
    """Keep rows for a specific department."""
    return filter(lambda r: r["department"] == dept, rows)


# ─── Higher-order pipeline builder ────────────────────────────────────────────

def pipeline(*funcs: Callable) -> Callable:
    """
    Compose a sequence of single-argument functions into one callable.
    pipeline(f, g, h)(x)  →  h(g(f(x)))
    """
    def composed(value):
        for f in funcs:
            value = f(value)
        return value
    return composed


# ─── Generators for memory-efficient processing ────────────────────────────────

def row_iterator(rows: Iterable) -> Iterator[dict]:
    """
    Convert each sqlite3.Row to a plain dict, yielding one at a time.
    Acts as a controlled iterator over query results.
    """
    for row in rows:
        processing_logger.debug("Processing row: %s", list(dict(row).items())[:2])
        yield dict(row)


def chunked(iterable: Iterable, size: int = 5) -> Iterator[list]:
    """Yield successive fixed-size chunks from an iterable."""
    chunk: list = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


# ─── Aggregation helpers ───────────────────────────────────────────────────────

@log_execution_time(processing_logger)
def group_by(rows: Iterable[dict], key: str) -> dict[Any, list[dict]]:
    """Group a flat list of dicts by a given key."""
    groups: dict[Any, list[dict]] = {}
    for row in rows:
        groups.setdefault(row[key], []).append(row)
    processing_logger.info("group_by('%s') produced %d groups", key, len(groups))
    return groups


def average(values: Iterable[float]) -> float:
    total, count = 0.0, 0
    for v in values:
        total += v
        count += 1
    return round(total / count, 2) if count else 0.0