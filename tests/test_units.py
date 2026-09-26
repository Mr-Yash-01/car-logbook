#!/usr/bin/env python3
"""Reading input, the calendar, validation, settings and the allocation maths."""

from __future__ import annotations

import calendar
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, group, refuses, report          # noqa: E402

import logbook as L                                        # noqa: E402
from logbook.config import Config, normalise_config        # noqa: E402


# ===========================================================================
group("A. Reading what people type")
# ===========================================================================

for raw, expect in [("01/07/2025", date(2025, 7, 1)), ("2025-07-01", date(2025, 7, 1)),
                    ("01-07-2025", date(2025, 7, 1)), ("01/07/25", date(2025, 7, 1)),
                    ("29/02/2024", date(2024, 2, 29))]:
    check(f"date {raw!r}", L.parse_date(raw) == expect, L.parse_date(raw))
for raw in ["31/02/2025", "29/02/2025", "13/13/2025", "tomorrow", "", "01/07"]:
    check(f"date {raw!r} refused", L.parse_date(raw) is None)

check("days Fri,Sat,Sun", L.parse_days("fri,sat,sun") == [4, 5, 6])
check("days Mon-Fri", L.parse_days("Mon-Fri") == [0, 1, 2, 3, 4])
check("days wrap Sun-Tue", L.parse_days("sun-tue") == [0, 1, 6])
check("days de-duplicated", L.parse_days("mon,mon,mon") == [0])
check("days nonsense falls back", L.parse_days("someday") == [4, 5, 6])
check("day names read back", L.name_days([4, 5, 6]) == "Fri, Sat and Sun")
check("one day reads back", L.name_days([2]) == "Wed")

for typed, expect in [("45,230, 55,230", (45230, 55230)), ("45230 to 55230", (45230, 55230)),
                      ("1,234,567 to 1,244,567", (1234567, 1244567))]:
    got = tuple(int(n) for n in L.parse_numbers(typed)[:2])
    check(f"numbers in {typed!r}", got == expect, got)
check("decimals survive", L.parse_numbers("2.5 per km") == [2.5])
check("no numbers", L.parse_numbers("none") == [])

check("amount strips $ and commas", L.parse_amount("$5,000.50", "x") == 5000.5)
check("amount minimum enforced", refuses(L.parse_amount, "-1", "x", minimum=0)[0])
check("amount maximum enforced", refuses(L.parse_amount, "5", "x", maximum=1)[0])
check("amount rejects words", refuses(L.parse_amount, "heaps", "x")[0])
for typed in ("85", "85%", "0.85"):
    check(f"share {typed!r} reads as 0.85", abs(L.parse_share(typed, "x") - 0.85) < 1e-9)
check("share of 100 is all of it", L.parse_share("100", "x") == 1.0)
check("share above 100 refused", refuses(L.parse_share, "140", "x")[0])

check("control characters stripped", L.sanitize_text("a\x07b\x00c") == "abc")
check("direction overrides stripped", L.sanitize_text("safe‮reversed") == "safereversed")
check("length capped", len(L.sanitize_text("x" * 9000)) == 500)
check("unicode kept", L.sanitize_text("café — naïve") == "café — naïve")
check("sheet name cleaned", L.sanitize_sheet_name("a[b]c:d*e?f/g\\h") == "a-b-c-d-e-f-g-h")
check("sheet name capped", len(L.sanitize_sheet_name("y" * 60)) == 31)
check("sheet name empty falls back", L.sanitize_sheet_name("  ") == "Logbook")


# ===========================================================================
group("B. The calendar")
# ===========================================================================

blocks = L.month_blocks(date(2024, 1, 15), date(2024, 5, 10))
lengths = {first.strftime("%b"): length for _k, first, _l, _u, length in blocks}
check("leap February is 29 days", lengths["Feb"] == 29)
check("April is 30", lengths["Apr"] == 30 and lengths["Mar"] == 31)
check("non-leap February is 28",
      L.month_blocks(date(2025, 2, 1), date(2025, 3, 1))[0][4] == 28)
check("part month counts days used",
      L.month_blocks(date(2024, 1, 15), date(2024, 1, 31))[0][3] == 17)
check("December rolls into January",
      [b[0] for b in L.month_blocks(date(2025, 12, 20), date(2026, 1, 10))]
      == ["2025-12", "2026-01"])
long_span = L.month_blocks(date(2024, 1, 1), date(2026, 12, 31))
check("36 months across three years", len(long_span) == 36)
check("every block matches the calendar",
      all(length == calendar.monthrange(first.year, first.month)[1]
          for _k, first, _l, _u, length in long_span))

check("financial year before July", L.financial_year_of(date(2025, 6, 30)) == "2024-25")
check("financial year from July", L.financial_year_of(date(2025, 7, 1)) == "2025-26")
check("bounds", L.financial_year_bounds("2025-26") == (date(2025, 7, 1), date(2026, 6, 30)))
check("next year", L.next_financial_year("2025-26") == "2026-27")
check("one year does not span", not L.spans_financial_years(date(2025, 7, 1), date(2025, 9, 1)))
check("crossing June does span", L.spans_financial_years(date(2025, 5, 1), date(2025, 9, 1)))
years = L.financial_years_in(date(2025, 5, 1), date(2026, 9, 1))
check("three years listed", [y[0] for y in years] == ["2024-25", "2025-26", "2026-27"])
check("each year clipped to the period",
      years[0][1] == date(2025, 5, 1) and years[-1][2] == date(2026, 9, 1))
check("counting weekdays", L.count_weekdays(date(2025, 7, 1), date(2025, 7, 31), [4, 5, 6]) == 12)


# ===========================================================================
group("C. Field checks")
# ===========================================================================

for value, ok in [("ABC123", True), ("abc 123", True), ("AB-12-CD", True),
                  ("ABCDEFGH", False), ("AB*123", False), ("=cmd|x", False),
                  ("", False), ("<script>", False), ("A" * 30, False)]:
    check(f"registration {value!r} {'accepted' if ok else 'refused'}",
          (not refuses(L.clean_registration, value)[0]) == ok)
check("registration tidied", L.clean_registration("abc 123") == "ABC123")
check("registration optional when told", L.clean_registration("", required=False) == "")

for value, ok in [("51824753556", True), ("51 824 753 556", True),
                  ("12345678901", False), ("123", False), ("abcdefghijk", False)]:
    check(f"ABN {value!r} {'accepted' if ok else 'refused'}",
          (not refuses(L.clean_abn, value)[0]) == ok)
check("ABN spaced", L.clean_abn("51824753556") == "51 824 753 556")
check("no ABN is fine", L.clean_abn("") == "")

for value, ok in [("1.8L", True), ("1798cc", True), ("2.0 (turbo)", True), ("V8", True),
                  ("biggish", False), ("", False), ("=1+1", False)]:
    check(f"engine {value!r} {'accepted' if ok else 'refused'}",
          (not refuses(L.clean_engine, value)[0]) == ok)
for value, ok in [("Toyota", True), ("Mercedes-Benz", True), ("Mazda CX-5", True),
                  ("=HYPERLINK(1)", False), ("<script>", False), ("x" * 60, False)]:
    check(f"make {value!r} {'accepted' if ok else 'refused'}",
          (not refuses(L.clean_vehicle_word, value, "make")[0]) == ok)
for value, ok in [("Yash Vadukiya", True), ("O'Brien", True), ("Anne-Marie Smith", True),
                  ("=cmd", False), ("2Pac", False), ("x" * 80, False)]:
    check(f"name {value!r} {'accepted' if ok else 'refused'}",
          (not refuses(L.clean_person, value)[0]) == ok)
check("odometer reads thousands", L.clean_odometer("45,230", "x") == 45230)
for bad in ("-1", "9000000", "lots"):
    check(f"odometer {bad!r} refused", refuses(L.clean_odometer, bad, "Reading")[0])
check("year in range", L.clean_year("2021") == "2021")
check("year too old refused", refuses(L.clean_year, "1850")[0])
check("wordings de-duplicated", L.clean_wordings(["A", "a", " A ", "B"]) == ["A", "B"])
check("wordings capped", len(L.clean_wordings([f"x{i}" for i in range(200)])) == L.MAX_WORDINGS)
check("wordings fall back", L.clean_wordings([], ["Default"]) == ["Default"])


# ===========================================================================
group("D. Settings")
# ===========================================================================

cfg = Config(work_days=[], business_share_on_work_days=5, max_km_per_day=1,
             max_business_km_per_day=0, min_journey_km=9999, seed="x",
             work_type="taxi", sheet_mode="whatever", city="atlantis",
             rideshare_reasons=[], private_reasons=["  "])
notes = normalise_config(cfg)
check("empty work days repaired", cfg.work_days == [4, 5, 6])
check("share above 1 clamped", cfg.business_share_on_work_days == 1.0)
check("zero cap repaired", cfg.max_business_km_per_day >= 1)
check("daily total lifted to the business cap",
      cfg.max_km_per_day >= cfg.max_business_km_per_day)
check("smallest journey pulled under the caps",
      cfg.min_journey_km <= min(cfg.max_business_km_per_day, cfg.max_private_km_per_day))
check("unknown work type repaired", cfg.work_type == "rideshare")
check("unknown sheet mode repaired", cfg.sheet_mode == "combined")
check("unknown city repaired", cfg.city == "brisbane")
check("empty wording restored", cfg.rideshare_reasons and cfg.private_reasons)
check("areas filled from the city", len(cfg.rideshare_destinations) > 4)
check("bad seed repaired", isinstance(cfg.seed, int))
check("every repair reported", len(notes) >= 6, len(notes))
check("running it twice changes nothing", normalise_config(cfg) == [])

for city in L.city_names():
    c = Config(city=city)
    normalise_config(c)
    check(f"{city} has its own areas", len(c.rideshare_destinations) >= 5)

check("a share of zero is refused as a work day",
      Config(business_share_on_work_days=0) is not None)
zero = Config(business_share_on_work_days=0)
normalise_config(zero)
check("and repaired to a sensible share", zero.business_share_on_work_days > 0)


# ===========================================================================
group("E. Spreading kilometres without losing any")
# ===========================================================================

rng = random.Random(11)
days = list(range(20))
for total in (0, 1, 7, 500, 2999, 3000):
    caps = {d: 150 for d in days}
    out = L.allocate(days, total, rng, caps, 5, 0.3)
    check(f"{total} km comes out exactly", sum(out.values()) == total)
    check(f"{total} km respects the caps", all(v <= 150 for v in out.values()))
check("more than the days can hold is refused",
      refuses(L.allocate, days, 5000, rng, {d: 150 for d in days}, 5, 0.0)[0])

leaks = 0
for _ in range(3000):
    caps = {d: rng.choice([70, 150, 350]) for d in range(rng.randint(2, 20))}
    alloc = {d: rng.randint(0, caps[d]) for d in caps}
    want = sum(alloc.values())
    got = sum(L.enforce_min(dict(alloc), rng.choice([0, 5, 25, 200]), caps).values())
    leaks += (got != want)
check("folding away small trips never loses a kilometre (3000 cases)", leaks == 0, leaks)

targets, total = L.month_targets_from({"a": 1666.666, "b": 1666.666, "c": 1666.668})
check("fractions round up to business", total == 5000 and sum(targets.values()) == 5000)
check("float dust adds no stray kilometre",
      L.month_targets_from({"a": 2500.0000000001})[1] == 2500)
check("percentile of nothing", L.percentile([], 0.7) == 0)
check("percentile picks a real value", L.percentile([10, 20, 30, 40], 0.7) in (30, 40))

report("Units")
