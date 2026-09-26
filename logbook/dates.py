"""Calendar work: days in a period, real month lengths, Australian financial years."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

MIN_YEAR, MAX_YEAR = 1990, 2100
MAX_PERIOD_DAYS = 3660          # ten years; past that the sheet stops being useful

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]
DAY_ABBR = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def parse_date(raw):
    """Read a date a person typed. Returns None rather than raising."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(str(raw).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def daterange(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def month_blocks(start: date, end: date) -> list:
    """[(YYYY-MM, first day in period, last day in period, days used, days in month)]

    Month lengths come from the calendar, so 28, 29, 30 and 31 all come out right.
    """
    out = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        length = calendar.monthrange(year, month)[1]
        first = max(start, date(year, month, 1))
        last = min(end, date(year, month, length))
        out.append((f"{year:04d}-{month:02d}", first, last, (last - first).days + 1, length))
        month = 1 if month == 12 else month + 1
        year = year + 1 if month == 1 else year
    return out


# --- Australian financial year: 1 July to 30 June ---------------------------

def financial_year_of(day: date) -> str:
    """The label for the year a date falls in, e.g. 2025-26."""
    return (f"{day.year}-{str(day.year + 1)[-2:]}" if day.month >= 7
            else f"{day.year - 1}-{str(day.year)[-2:]}")


def financial_year_bounds(label: str):
    year = int(str(label).split("-")[0])
    return date(year, 7, 1), date(year + 1, 6, 30)


def next_financial_year(label: str) -> str:
    year = int(str(label).split("-")[0]) + 1
    return f"{year}-{str(year + 1)[-2:]}"


def financial_years_in(start: date, end: date) -> list:
    """[(label, first day in period, last day in period)] for every year touched."""
    out = []
    label = financial_year_of(start)
    while True:
        fy_start, fy_end = financial_year_bounds(label)
        out.append((label, max(start, fy_start), min(end, fy_end)))
        if fy_end >= end:
            break
        label = next_financial_year(label)
    return out


def spans_financial_years(start: date, end: date) -> bool:
    return financial_year_of(start) != financial_year_of(end)


def parse_days(raw, fallback=(4, 5, 6)) -> list:
    """Read 'Fri,Sat,Sun' or 'mon-fri' into weekday numbers. Never raises."""
    chosen = []
    for part in str(raw or "").lower().replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            first, _, last = part.partition("-")
            a = next((i for i, n in enumerate(DAY_ABBR) if n.startswith(first[:3])), None)
            b = next((i for i, n in enumerate(DAY_ABBR) if n.startswith(last[:3])), None)
            if a is None or b is None:
                continue
            i = a
            while True:
                chosen.append(i)
                if i == b:
                    break
                i = (i + 1) % 7
        else:
            idx = next((i for i, n in enumerate(DAY_ABBR) if n.startswith(part[:3])), None)
            if idx is not None:
                chosen.append(idx)
    return sorted(set(chosen)) or list(fallback)


def name_days(weekdays) -> str:
    """'Fri, Sat and Sun' - for reading back to a person."""
    names = [DAY_NAMES[d][:3] for d in sorted(set(weekdays))]
    if not names:
        return "no days"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def count_weekdays(start: date, end: date, weekdays) -> int:
    weekdays = set(weekdays)
    return sum(1 for day in daterange(start, end) if day.weekday() in weekdays)
