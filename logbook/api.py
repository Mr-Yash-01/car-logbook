"""One call in, one spreadsheet out - what every front end uses.

`generate(settings)` validates, builds and returns the file in memory. It raises
LogbookError with a message fit to show a person, so a bot or a web form can put
it straight on screen.
"""

from __future__ import annotations

import calendar
import json

from .allocate import month_targets_from
from .config import (Config, DOLLARS_PER_BUSINESS_KM, MAX_JOURNEY_ROWS_WARN,
                     as_dict, config_from, normalise_config)
from .dates import (MAX_PERIOD_DAYS, financial_years_in, month_blocks, parse_date,
                    spans_financial_years)
from .errors import LogbookError, capture_notes, fail, note
from .journeys import build_journeys
from .pattern import assess, pattern_from
from .text import INCOME_MONTH_MAX, ODOMETER_MAX
from .workbook import workbook_bytes, write_workbook


def business_by_month(monthly_income: dict, dollars_per_km=DOLLARS_PER_BUSINESS_KM):
    rate = dollars_per_km or DOLLARS_PER_BUSINESS_KM
    return {k: v / rate for k, v in monthly_income.items()}


def read_income(cfg, start, end) -> dict:
    """Month-by-month income, pro-rated for a part month when asked."""
    if not isinstance(cfg.monthly_income, dict):
        fail('Income must be given as an object of "YYYY-MM": amount pairs')
    income = {}
    for key, value in cfg.monthly_income.items():
        if not (isinstance(key, str) and len(key) == 7 and key[4] == "-"
                and key[:4].isdigit() and key[5:].isdigit() and 1 <= int(key[5:]) <= 12):
            fail(f'The income month "{key}" should look like "2025-07"')
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            fail(f"Income for {key} must be a number of 0 or more")
        if value > INCOME_MONTH_MAX:
            fail(f"Income for {key} of {value:,.0f} looks wrong - the most one month "
                 f"can hold is {INCOME_MONTH_MAX:,}")
        income[key] = float(value)

    needed = {block[0] for block in month_blocks(start, end)}
    spare = sorted(set(income) - needed)
    if spare:
        note(f"Income given for months outside the period was ignored: {', '.join(spare)}")
    for key, month_start, _month_end, used, length in month_blocks(start, end):
        if key not in income:
            fail(f"No income given for {month_start:%B %Y} - every month in the period "
                 f"needs a figure")
        if cfg.prorate_partial_months and used < length:
            scaled = income[key] * used / length
            note(f"{month_start:%B %Y}: {used} of its {length} days fall in the period, "
                 f"so income was pro-rated to ${scaled:,.2f}")
            income[key] = scaled
    return {k: v for k, v in income.items() if k in needed}


def prepare(data):
    """Validate settings and work out the period, odometer and business kilometres."""
    cfg = config_from(data)
    start = parse_date(cfg.start_date)
    end = parse_date(cfg.end_date)
    if not start:
        fail(f"Could not read the start date: {cfg.start_date}")
    if not end:
        fail(f"Could not read the end date: {cfg.end_date}")
    if end <= start:
        fail("The end date has to be after the start date.")
    if (end - start).days + 1 > MAX_PERIOD_DAYS:
        fail(f"The period is longer than {MAX_PERIOD_DAYS:,} days")

    if cfg.start_odometer is None:
        fail("The start odometer reading is needed")
    try:
        start_odo = int(cfg.start_odometer)
    except (TypeError, ValueError):
        fail("The start odometer reading must be a whole number of kilometres")
    if not 0 <= start_odo <= ODOMETER_MAX:
        fail(f"The start odometer reading must be between 0 and {ODOMETER_MAX:,} km")
    try:
        if cfg.end_odometer is not None:
            end_odo = int(cfg.end_odometer)
        elif cfg.total_km is not None:
            end_odo = start_odo + int(cfg.total_km)
        else:
            fail("Either the end odometer reading or the total kilometres is needed")
    except (TypeError, ValueError):
        fail("The odometer readings must be whole numbers of kilometres")
    if end_odo <= start_odo:
        fail(f"The end odometer ({end_odo:,}) has to be higher than the start "
             f"({start_odo:,})")
    if end_odo > ODOMETER_MAX:
        fail(f"The end odometer reading cannot be above {ODOMETER_MAX:,} km")

    income = read_income(cfg, start, end)
    business = business_by_month(income, cfg.dollars_per_km)
    _targets, business_total = month_targets_from(business)
    if business_total > end_odo - start_odo:
        fail(f"What you earned works out at {business_total:,} business km, but the "
             f"odometer readings only cover {end_odo - start_odo:,} km. Raise the "
             f"closing reading, or check the income.")
    return cfg, start, end, start_odo, end_odo, income, business


def month_pressure_for(business, start, end):
    """[(label, first day, last day, business km)] - what each month has to carry."""
    targets, _total = month_targets_from(business)
    return [(f"{first:%B %Y}", first, last, targets.get(key, 0))
            for key, first, last, _used, _length in month_blocks(start, end)]


def check_pattern(cfg, start, end, business, total_km):
    """Does the travel pattern hold these kilometres, month by month? An Assessment."""
    _targets, business_total = month_targets_from(business)
    return assess(pattern_from(cfg), start, end, business_total, total_km,
                  month_pressure_for(business, start, end))


def split_sections(cfg, rows, start, end, start_odo, end_odo, income):
    """The worksheets to write: one, or one per financial year."""
    combined = (cfg.sheet_mode != "per-year"
                or not spans_financial_years(start, end))
    if combined:
        name = cfg.sheet_name or "Logbook"
        return [(name, rows, start, end, start_odo, end_odo, sum(income.values()))]

    sections = []
    for label, first, last in financial_years_in(start, end):
        part = [r for r in rows if first <= r["date"] <= last]
        if not part:
            continue
        opening = part[0]["odo_start"]
        closing = part[-1]["odo_end"]
        earned = sum(amount for key, amount in income.items()
                     if any(key == block[0] and block[1] <= last and block[2] >= first
                            for block in month_blocks(start, end)))
        renumbered = [dict(r, n=i + 1) for i, r in enumerate(part)]
        sections.append((f"{label} logbook", renumbered, first, last,
                         opening, closing, earned))
    return sections or [(cfg.sheet_name or "Logbook", rows, start, end,
                         start_odo, end_odo, sum(income.values()))]


def suggested_filename(cfg, start, end) -> str:
    rego = "".join(ch for ch in (cfg.registration or "") if ch.isalnum()) or "car"
    return f"logbook-{rego}-{start:%Y-%m-%d}-to-{end:%Y-%m-%d}.xlsx"


def generate(settings) -> dict:
    """Settings in, spreadsheet out.

    Returns {"bytes", "filename", "summary", "sheets", "notes", "warnings"}.
    """
    with capture_notes() as collected:
        cfg = config_from(settings)
        notes = normalise_config(cfg)
        cfg, start, end, start_odo, end_odo, income, business = prepare(cfg)
        rows, summary = build_journeys(cfg, start, end, start_odo, end_odo, business)
        if not rows:
            fail("No kilometres were allocated to any day, so there is nothing to record")
        sections = split_sections(cfg, rows, start, end, start_odo, end_odo, income)
        data = workbook_bytes(cfg, sections)
        notes = notes + collected

    if len(rows) > MAX_JOURNEY_ROWS_WARN:
        notes.append(f"{len(rows):,} journey rows is a very long sheet.")
    summary = dict(summary)
    warnings = summary.pop("notes", [])
    summary.update({"start": start, "end": end, "days": (end - start).days + 1,
                    "start_odometer": start_odo, "end_odometer": end_odo,
                    "income": sum(income.values()),
                    "sheets": [s[0] for s in sections]})
    return {"bytes": data, "filename": suggested_filename(cfg, start, end),
            "summary": summary, "sheets": [s[0] for s in sections],
            "notes": notes, "warnings": warnings}


def load_config(path):
    """Read a JSON config from disk and prepare it."""
    try:
        with open(path) as handle:
            data = json.load(handle)
    except FileNotFoundError:
        fail(f"No config file at {path}")
    except IsADirectoryError:
        fail(f"{path} is a folder, not a config file")
    except PermissionError:
        fail(f"No permission to read {path}")
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON - {exc.msg} (line {exc.lineno}, "
             f"column {exc.colno})")
    if not isinstance(data, dict):
        fail(f"{path} must hold a JSON object, not a {type(data).__name__}")
    return prepare(data)


def write_config_template(path):
    cfg = Config()
    cfg.owner_name = "Your Name"
    cfg.start_odometer = 45230
    cfg.end_odometer = 55230
    cfg.monthly_income = {"2025-07": 5000, "2025-08": 5000, "2025-09": 5000}
    data = as_dict(cfg)
    data.pop("dollars_per_km", None)          # worked out internally, not a setting
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2)
    return path
