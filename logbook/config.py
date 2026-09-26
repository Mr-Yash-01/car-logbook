"""Every setting in one place, with the checks that repair or refuse them.

The travel pattern works like this now:
  * business kilometres go only on the days the driver says they work
  * on a work day, a share says how much of that day's driving is business;
    the rest of that day is private
  * days that are not work days carry private travel only
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date

from . import wording
from .dates import parse_date, parse_days
from .errors import fail, note
from .text import (clean_abn, clean_engine, clean_odometer, clean_person,
                   clean_registration, clean_vehicle_word, clean_wordings, clean_year,
                   sanitize_sheet_name)

DOLLARS_PER_BUSINESS_KM = 2.0     # fixed internally; never asked and never shown
LONG_DAY_PERCENTILE = 0.70        # above this a day is written up as two areas
MAX_JOURNEY_ROWS_WARN = 5000
PLAUSIBLE_DAILY_KM = 800

WORK_TYPES = ("rideshare", "delivery", "both")
SHEET_MODES = ("combined", "per-year")


@dataclass
class Config:
    # Period
    start_date: str = "2025-07-01"
    end_date: str = "2025-09-22"
    sheet_mode: str = "combined"       # combined | per-year, when the period spans years

    # Income
    monthly_income: dict = field(default_factory=dict)      # "YYYY-MM" -> dollars
    prorate_partial_months: bool = True
    dollars_per_km: float = DOLLARS_PER_BUSINESS_KM

    # Vehicle and owner
    owner_name: str = ""
    abn: str = ""
    make: str = "Toyota"
    model: str = "Corolla"
    year_of_manufacture: str = ""
    engine_capacity: str = "1.8L"
    registration: str = "ABC123"

    # Odometer
    start_odometer: int | None = None
    end_odometer: int | None = None
    total_km: int | None = None

    # What the driving is for
    work_type: str = "rideshare"
    rideshare_share: float = 0.5       # only when work_type is "both"

    # Travel pattern
    work_days: list = field(default_factory=lambda: [4, 5, 6])   # Mon=0 .. Sun=6
    business_share_on_work_days: float = 0.85
    max_km_per_day: int = 420
    max_business_km_per_day: int = 350
    max_private_km_per_day: int = 150
    min_journey_km: int = 5
    rest_day_chance: float = 0.10      # a work day with no work travel
    quiet_day_chance: float = 0.35     # a day with no private travel
    auto_cap_ceiling: int = 600

    # Wording
    city: str = wording.DEFAULT_CITY
    rideshare_reasons: list = field(default_factory=lambda: list(wording.RIDESHARE_REASONS))
    delivery_reasons: list = field(default_factory=lambda: list(wording.DELIVERY_REASONS))
    private_reasons: list = field(default_factory=lambda: list(wording.PRIVATE_REASONS))
    rideshare_destinations: list = field(default_factory=list)   # empty = city defaults
    delivery_destinations: list = field(default_factory=list)

    # Output
    sheet_name: str = "Logbook"
    output: str = "car_logbook.xlsx"
    seed: int = 42


def as_dict(cfg: Config) -> dict:
    return asdict(cfg)


def config_from(data) -> Config:
    """Build a Config from a plain dict, ignoring anything it does not know."""
    if isinstance(data, Config):
        return data
    if not isinstance(data, dict):
        fail("Settings must be given as an object of name: value pairs")
    unknown = set(data) - set(Config.__dataclass_fields__)
    if unknown:
        note(f"Ignoring unknown settings: {', '.join(sorted(unknown))}")
    return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})


def _clamp_fraction(cfg: Config, name: str, notes: list):
    value = getattr(cfg, name)
    default = getattr(Config(), name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        setattr(cfg, name, default)
        notes.append(f"{name} was not a number - using {default}.")
    elif not 0.0 <= value <= 1.0:
        clamped = min(1.0, max(0.0, float(value)))
        setattr(cfg, name, clamped)
        notes.append(f"{name} was {value} - clamped to {clamped}.")


def normalise_config(cfg: Config) -> list:
    """Repair what can be repaired, refuse what cannot. Returns notes to show."""
    notes: list = []
    default = Config()

    if not isinstance(cfg.dollars_per_km, (int, float)) or cfg.dollars_per_km <= 0:
        cfg.dollars_per_km = DOLLARS_PER_BUSINESS_KM

    mode = str(cfg.sheet_mode or "").strip().lower()
    if mode not in SHEET_MODES:
        if mode:
            notes.append(f"sheet_mode must be {' or '.join(SHEET_MODES)} - using combined.")
        mode = "combined"
    cfg.sheet_mode = mode

    kind = str(cfg.work_type or "").strip().lower()
    if kind not in WORK_TYPES:
        notes.append(f"work_type must be one of {', '.join(WORK_TYPES)} - using rideshare.")
        kind = "rideshare"
    cfg.work_type = kind

    days = sorted({int(d) for d in (cfg.work_days or [])
                   if isinstance(d, (int, float)) and 0 <= int(d) <= 6})
    if not days:
        days = list(default.work_days)
        notes.append("No work days given - using Fri, Sat and Sun.")
    cfg.work_days = days

    for name in ("rideshare_share", "business_share_on_work_days",
                 "rest_day_chance", "quiet_day_chance"):
        _clamp_fraction(cfg, name, notes)

    if cfg.business_share_on_work_days <= 0:
        cfg.business_share_on_work_days = default.business_share_on_work_days
        notes.append("A work day has to be at least partly business - share set to "
                     f"{default.business_share_on_work_days:.0%}.")

    for name in ("max_km_per_day", "max_business_km_per_day",
                 "max_private_km_per_day", "auto_cap_ceiling"):
        value = getattr(cfg, name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 1:
            setattr(cfg, name, getattr(default, name))
            notes.append(f"{name} must be at least 1 - using {getattr(default, name)}.")
        else:
            setattr(cfg, name, int(value))

    if not isinstance(cfg.min_journey_km, (int, float)) or cfg.min_journey_km < 0:
        cfg.min_journey_km = default.min_journey_km
        notes.append(f"min_journey_km cannot be negative - using {default.min_journey_km}.")
    cfg.min_journey_km = int(cfg.min_journey_km)

    smallest = min(cfg.max_business_km_per_day, cfg.max_private_km_per_day)
    if cfg.min_journey_km > smallest:
        notes.append(f"The smallest journey ({cfg.min_journey_km} km) was above a daily "
                     f"cap ({smallest} km) - lowered to {smallest} km.")
        cfg.min_journey_km = smallest
    if cfg.max_km_per_day < cfg.max_business_km_per_day:
        notes.append(f"The daily total was below the business cap - raised to "
                     f"{cfg.max_business_km_per_day} km.")
        cfg.max_km_per_day = cfg.max_business_km_per_day
    if cfg.auto_cap_ceiling < cfg.max_km_per_day:
        cfg.auto_cap_ceiling = cfg.max_km_per_day

    city = str(cfg.city or wording.DEFAULT_CITY).strip().lower()
    if city not in wording.AREAS:
        if city:
            notes.append(f"No area list for \"{city}\" - using {wording.DEFAULT_CITY}.")
        city = wording.DEFAULT_CITY
    cfg.city = city

    cfg.rideshare_reasons = clean_wordings(cfg.rideshare_reasons, wording.RIDESHARE_REASONS)
    cfg.delivery_reasons = clean_wordings(cfg.delivery_reasons, wording.DELIVERY_REASONS)
    cfg.private_reasons = clean_wordings(cfg.private_reasons, wording.PRIVATE_REASONS)
    cfg.rideshare_destinations = clean_wordings(cfg.rideshare_destinations,
                                                wording.rideshare_areas(city))
    cfg.delivery_destinations = clean_wordings(cfg.delivery_destinations,
                                               wording.delivery_areas(city))

    cfg.owner_name = clean_person(cfg.owner_name, "name")
    cfg.abn = clean_abn(cfg.abn)
    cfg.make = clean_vehicle_word(cfg.make, "make", required=False)
    cfg.model = clean_vehicle_word(cfg.model, "model", required=False)
    cfg.engine_capacity = clean_engine(cfg.engine_capacity, required=False)
    cfg.registration = clean_registration(cfg.registration, required=False)
    cfg.year_of_manufacture = clean_year(cfg.year_of_manufacture)
    if not cfg.make and not cfg.model:
        notes.append("No make or model given - the sheet will show blanks there.")

    tidy = sanitize_sheet_name(cfg.sheet_name)
    if tidy != (cfg.sheet_name or ""):
        notes.append(f'Sheet name adjusted to "{tidy}".')
    cfg.sheet_name = tidy

    if not isinstance(cfg.seed, (int, float)) or isinstance(cfg.seed, bool):
        cfg.seed = default.seed
        notes.append(f"The shuffle number was not a number - using {default.seed}.")
    cfg.seed = int(cfg.seed)
    return notes
