from __future__ import annotations

from datetime import date, datetime, timezone

# Word Territory Japanese daily challenge helper.
# Keep this file dependency-light: main.py imports daily.py before engine.py.
# JP v31 has 8 configured Japanese openings in language_profiles/ja.py.
_OPENING_COUNT = 8
_EPOCH = date(2026, 1, 1)


def get_today_utc() -> str:
    """Return today's date in UTC as YYYY-MM-DD."""
    return datetime.now(timezone.utc).date().isoformat()


def _parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except Exception:
        return datetime.now(timezone.utc).date()


def date_to_day_number(date_str: str) -> int:
    """
    Convert YYYY-MM-DD to a stable 1-based daily challenge number.
    """
    d = _parse_date(date_str)
    return max(1, (d - _EPOCH).days + 1)


def date_to_opening_idx(date_str: str) -> int:
    """
    Select a deterministic opening index for the daily challenge.
    """
    return (date_to_day_number(date_str) - 1) % _OPENING_COUNT
