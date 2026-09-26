"""Car logbook generator.

    from logbook import generate
    result = generate({...})        # result["bytes"] is the spreadsheet

The modules underneath, in the order work flows through them:
    errors     failures that carry a message a person can read
    text       reading and checking what people type
    dates      periods, real month lengths, Australian financial years
    wording    default reasons and areas
    config     every setting, and the checks that repair or refuse them
    allocate   spreading kilometres over days without losing one
    pattern    whether a travel pattern fits, and what would
    journeys   totals into a list of journeys
    workbook   the spreadsheet itself
    api        settings in, spreadsheet out
"""

from .allocate import (allocate, enforce_caps, enforce_min, largest_remainder,
                       lift_caps, month_targets_from, percentile)
from .api import (business_by_month, check_pattern, generate, load_config,
                  month_pressure_for, prepare, read_income, split_sections,
                  suggested_filename, write_config_template)
from .config import (Config, DOLLARS_PER_BUSINESS_KM, MAX_JOURNEY_ROWS_WARN,
                     PLAUSIBLE_DAILY_KM, SHEET_MODES, WORK_TYPES, as_dict,
                     config_from, normalise_config)
from .dates import (DAY_ABBR, DAY_NAMES, MAX_PERIOD_DAYS, MAX_YEAR, MIN_YEAR,
                    count_weekdays, daterange, financial_year_bounds,
                    financial_year_of, financial_years_in, month_blocks, name_days,
                    next_financial_year, parse_date, parse_days,
                    spans_financial_years)
from .errors import LogbookError, capture_notes, fail, note
from .journeys import assign_work_types, build_journeys, pick_destination
from .pattern import Assessment, Pattern, apply_to, assess, describe, measure, \
    month_pressure, pattern_from, private_on_work_days, problems_with
from .text import (INCOME_MONTH_MAX, MAX_WORDINGS, ODOMETER_MAX, REGO_MAX, clean_abn,
                   clean_engine, clean_odometer, clean_person, clean_registration,
                   clean_vehicle_word, clean_wordings, clean_year, parse_amount,
                   parse_numbers, parse_share, sanitize_sheet_name, sanitize_text)
from .notebook import in_colab, make_logbook, spread_income
from .wording import (DELIVERY_REASONS, PRIVATE_REASONS, RIDESHARE_REASONS,
                      areas_for, city_names, delivery_areas, rideshare_areas)
from .workbook import fixed_timestamps, workbook_bytes, write_workbook

__all__ = [n for n in dir() if not n.startswith("_")]
