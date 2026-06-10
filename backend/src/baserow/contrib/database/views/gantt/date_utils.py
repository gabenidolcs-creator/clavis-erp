"""
Pure date math for the Gantt cascade reschedule (Story 3.10 / FR-10).

Kept dependency-free and DB-free so the cascade walk in
``TaskDependencyHandler`` and its unit tests can shift dates without rows. The
semantics mirror the frontend Timeline ``shiftDateValue`` (Story 3.7): a
date-only field round-trips as ``YYYY-MM-DD`` and a datetime field preserves its
time-of-day, with no naive-UTC arithmetic that would drift a unit across a
month-end or DST boundary — the date component moves by whole-day deltas only.

A predecessor/successor pair always references the SAME ``start_date_field`` and
``end_date_field`` of one table, but those two fields may differ in
``date_include_time`` (e.g. a date-only start and a datetime end). Comparison and
delta math therefore normalise every value to an aware UTC datetime (a date-only
value anchors at UTC midnight); the shift is then applied back in each field's
own canonical shape.
"""

from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Optional, Union

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

# A stored field value can arrive as a Python ``date``/``datetime`` (read off a
# row model instance) or as an ISO string (the predecessor's new dates posted by
# the client). Both are accepted everywhere here.
DateLike = Union[str, date, datetime, None]


def _parse(value: DateLike, date_include_time: bool) -> Optional[Union[date, datetime]]:
    """
    Parse a stored value or ISO string into a ``date`` (date-only field) or
    ``datetime`` (datetime field). Returns ``None`` for an empty value.
    """

    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        parsed: Union[date, datetime] = value
    elif isinstance(value, date):
        parsed = value
    else:
        # ISO string: try datetime first so a full timestamp keeps its time;
        # fall back to a bare date.
        dt = parse_datetime(value)
        if dt is not None:
            parsed = dt
        else:
            d = parse_date(value)
            if d is None:
                return None
            parsed = d

    if date_include_time:
        if isinstance(parsed, datetime):
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, dt_timezone.utc)
            return parsed.astimezone(dt_timezone.utc)
        # A date supplied for a datetime field anchors at UTC midnight.
        return datetime(parsed.year, parsed.month, parsed.day, tzinfo=dt_timezone.utc)

    # Date-only field: collapse any datetime to its date component.
    if isinstance(parsed, datetime):
        return parsed.date()
    return parsed


def to_datetime(value: DateLike, date_include_time: bool) -> Optional[datetime]:
    """
    Normalise any value to an aware UTC datetime for comparison / delta math. A
    date-only value anchors at UTC midnight so a date-only start and a datetime
    end of the same table compare consistently. Returns ``None`` when empty.
    """

    parsed = _parse(value, date_include_time)
    if parsed is None:
        return None
    if isinstance(parsed, datetime):
        return parsed
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=dt_timezone.utc)


def format_value(value: Union[date, datetime], date_include_time: bool) -> str:
    """
    Serialise a ``date``/``datetime`` back into the canonical stored ISO shape:
    a date-only field returns ``YYYY-MM-DD``; a datetime field returns a UTC ISO
    timestamp. Mirrors ``shiftDateValue``'s output discipline.
    """

    if date_include_time:
        if isinstance(value, datetime):
            if timezone.is_naive(value):
                value = timezone.make_aware(value, dt_timezone.utc)
            return value.astimezone(dt_timezone.utc).isoformat()
        return datetime(
            value.year, value.month, value.day, tzinfo=dt_timezone.utc
        ).isoformat()
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat()


def shift_value(value: DateLike, delta: timedelta, date_include_time: bool) -> Optional[str]:
    """
    Shift a stored value by ``delta`` and return it in canonical ISO form,
    preserving time-of-day for datetime fields and whole days for date-only
    fields (``date + timedelta`` uses only the day component, so a sub-day delta
    truncates for a date-only field — by design). Returns ``None`` for an empty
    origin value. Pure: no DB, no row.
    """

    parsed = _parse(value, date_include_time)
    if parsed is None:
        return None
    return format_value(parsed + delta, date_include_time)
