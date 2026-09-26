#!/usr/bin/env python3
"""The notebook entry point - the one call the Colab notebook makes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, group, refuses, report           # noqa: E402

import logbook as L                                          # noqa: E402


# ===========================================================================
group("A. The notebook entry point")
# ===========================================================================

import os                                                      # noqa: E402
import tempfile                                                # noqa: E402
from logbook.notebook import make_logbook, spread_income       # noqa: E402
from logbook.dates import parse_date                           # noqa: E402

here = os.getcwd()
os.chdir(tempfile.mkdtemp())
try:
    made = make_logbook(start_date="01/07/2025", weeks=12, income_per_month=5000,
                        start_odometer=45230, end_odometer=55230, make="Toyota",
                        model="Corolla", engine_capacity="1.8L",
                        registration="ABC123", download=False, quiet=True)
    check("the notebook call writes a file", made.exists() and made.suffix == ".xlsx")
    check("named after the plate and dates", "ABC123" in made.name, made.name)
    check("it really is a spreadsheet", made.read_bytes()[:2] == b"PK")

    named = make_logbook(start_date="01/07/2025", weeks=12, income_per_month=5000,
                         start_odometer=45230, end_odometer=55230, make="Toyota",
                         model="Corolla", engine_capacity="1.8L",
                         registration="ABC123", filename="mine", download=False,
                         quiet=True)
    check("a name of your own gets the right ending", named.name == "mine.xlsx")

    fixed = make_logbook(start_date="01/07/2025", weeks=12, income_per_month=9000,
                         start_odometer=20000, end_odometer=45000, make="Toyota",
                         model="Corolla", engine_capacity="1.8L",
                         registration="XYZ789", work_days="Sat", download=False,
                         quiet=True)
    check("an unworkable pattern is fixed rather than refused", fixed.exists())

    told, message = refuses(make_logbook, start_date="01/07/2025", weeks=12,
                            income_per_month=9000, start_odometer=20000,
                            end_odometer=45000, make="Toyota", model="Corolla",
                            engine_capacity="1.8L", registration="XYZ789",
                            work_days="Sat", accept_suggestion=False,
                            download=False, quiet=True)
    check("or explained, when you ask to decide yourself",
          told and "Closest workable pattern" in message, message[:80])

    for bad, needle in [(dict(start_date="soon"), "Could not read the start date"),
                        (dict(weeks=0), "between 1 and 104"),
                        (dict(weeks=500), "between 1 and 104"),
                        (dict(income_per_month=0), "business kilometres come from it"),
                        (dict(registration="ABCDEFGH"), "up to 7"),
                        (dict(end_odometer=20000), "higher than")]:
        args = dict(start_date="01/07/2025", weeks=12, income_per_month=5000,
                    start_odometer=45230, end_odometer=55230, make="Toyota",
                    model="Corolla", engine_capacity="1.8L", registration="ABC123",
                    download=False, quiet=True)
        args.update(bad)
        refused, message = refuses(make_logbook, **args)
        check(f"{list(bad)[0]}={list(bad.values())[0]!r} is explained",
              refused and needle in message, message[:70])

    start, end = parse_date("2025-07-01"), parse_date("2025-09-22")
    spread = spread_income(5000, start, end)
    check("one figure spreads over every month", len(spread) == 3)
    check("and a part month is scaled down", spread["2025-09"] < spread["2025-08"])
    check("a whole month is left alone", spread["2025-07"] == 5000)
finally:
    os.chdir(here)

report("Notebook")
