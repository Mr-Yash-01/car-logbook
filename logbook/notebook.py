"""Running the generator from a notebook - Colab, Jupyter, anywhere.

One call takes plain values, checks them, builds the spreadsheet and hands it
over. In Colab it goes straight to the browser's downloads; anywhere else it is
written beside the notebook.

    from logbook.notebook import make_logbook
    make_logbook(start_date="01/07/2025", weeks=12, income_per_month=5000, ...)
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from .api import business_by_month, check_pattern, generate, month_pressure_for
from .allocate import month_targets_from
from .config import Config, normalise_config
from .dates import (financial_years_in, month_blocks, name_days, parse_date,
                    parse_days, spans_financial_years)
from .errors import LogbookError, capture_notes, fail
from .pattern import apply_to, describe, pattern_from
from .text import parse_share


def in_colab() -> bool:
    try:
        import google.colab                                  # noqa: F401
        return True
    except Exception:                                        # noqa: BLE001
        return False


def spread_income(amount: float, start, end, prorate: bool = True) -> dict:
    """One monthly figure across the period, scaled down for any part month."""
    out = {}
    for key, first, _last, used, length in month_blocks(start, end):
        out[key] = amount * used / length if (prorate and used < length) else amount
    return out


def make_logbook(*, start_date: str, weeks: int = 12,
                 income_per_month: float = 0.0, monthly_income: dict | None = None,
                 start_odometer: int = 0, end_odometer: int = 0,
                 make: str = "", model: str = "", engine_capacity: str = "",
                 registration: str = "", owner_name: str = "", abn: str = "",
                 year_of_manufacture: str = "",
                 work_type: str = "rideshare", work_days: str = "Fri,Sat,Sun",
                 business_share_on_work_days="85%",
                 max_km_per_day: int = 420, max_business_km_per_day: int = 350,
                 max_private_km_per_day: int = 150,
                 city: str = "brisbane", sheet_per_financial_year: bool = True,
                 seed: int = 42, filename: str = "",
                 accept_suggestion: bool = True, download: bool = True,
                 quiet: bool = False):
    """Build the logbook and hand back the path it was written to.

    Everything is a plain value, so a notebook form can drive it. When the travel
    pattern cannot hold the kilometres, the closest workable pattern is applied
    for you (set accept_suggestion=False to be told instead), and it never
    records fewer business kilometres than your income supports.
    """
    say = (lambda *a: None) if quiet else print

    start = parse_date(start_date)
    if not start:
        fail(f"Could not read the start date: {start_date!r}. Try 01/07/2025.")
    weeks = int(weeks)
    if not 1 <= weeks <= 104:
        fail("Weeks has to be between 1 and 104.")
    end = start + timedelta(weeks=weeks, days=-1)

    income = dict(monthly_income) if monthly_income else spread_income(
        float(income_per_month), start, end)
    if not income or sum(income.values()) <= 0:
        fail("Enter what you earned - business kilometres come from it.")

    cfg = Config(
        start_date=start.isoformat(), end_date=end.isoformat(),
        monthly_income=income, prorate_partial_months=False,
        make=make, model=model, engine_capacity=engine_capacity,
        registration=registration, owner_name=owner_name, abn=abn,
        year_of_manufacture=year_of_manufacture,
        start_odometer=int(start_odometer), end_odometer=int(end_odometer),
        work_type=str(work_type).strip().lower(),
        work_days=parse_days(work_days),
        business_share_on_work_days=parse_share(business_share_on_work_days, "The share"),
        max_km_per_day=int(max_km_per_day),
        max_business_km_per_day=int(max_business_km_per_day),
        max_private_km_per_day=int(max_private_km_per_day),
        city=str(city).strip().lower(), seed=int(seed),
        sheet_mode="per-year" if sheet_per_financial_year else "combined")
    with capture_notes():
        normalise_config(cfg)

    say(f"Period: {start:%d %b %Y} to {end:%d %b %Y} ({(end - start).days + 1} days)")
    if spans_financial_years(start, end):
        years = ", ".join(label for label, _a, _b in financial_years_in(start, end))
        layout = "a sheet each" if cfg.sheet_mode == "per-year" else "one combined sheet"
        say(f"It crosses 30 June, covering {years} - {layout}.")
    say(f"Work days: {name_days(cfg.work_days)}. Business travel goes on those only.")

    total_km = int(end_odometer) - int(start_odometer)
    business = business_by_month(income)
    _targets, business_km = month_targets_from(business)
    verdict = check_pattern(cfg, start, end, business, total_km)
    if not verdict.ok:
        say("\nThat pattern will not hold these kilometres:")
        for problem in verdict.problems:
            say(f"  - {problem}")
        if verdict.suggestion is None:
            fail("Nothing close to that pattern works. Try more work days, a longer "
                 "period, or check the income and odometer figures.")
        if not accept_suggestion:
            fail("Closest workable pattern: " + describe(verdict.suggestion)
                 + " - set accept_suggestion=True to use it.")
        say("\nUsing the closest fit that still claims every business kilometre:")
        for change in verdict.changes:
            say(f"  - {change}")
        apply_to(cfg, verdict.suggestion)
        with capture_notes():
            normalise_config(cfg)

    result = generate(cfg)
    summary = result["summary"]
    path = Path(filename or result["filename"])
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")
    path.write_bytes(result["bytes"])

    say(f"\n{summary['journeys']} journeys, {summary['total_km']:,} km in total.")
    say(f"Business {summary['business_km']:,} km, private {summary['private_km']:,} km "
        f"- {summary['business_pct']:.1%} business use.")
    if len(result["sheets"]) > 1:
        say(f"Sheets: {', '.join(result['sheets'])}")
    for warning in result["warnings"]:
        say(f"! {warning}")
    say(f"Saved: {path}")

    if download and in_colab():
        try:
            from google.colab import files
            files.download(str(path))
            say("Your browser is downloading it now.")
        except Exception as exc:                             # noqa: BLE001
            say(f"(browser download unavailable: {exc})")
    return path
