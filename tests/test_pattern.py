#!/usr/bin/env python3
"""The travel pattern: where business may be recorded, and what to suggest when
the days cannot hold it."""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, group, refuses, report          # noqa: E402

import logbook as L                                        # noqa: E402
from logbook.config import Config, normalise_config        # noqa: E402

START, END = date(2025, 7, 1), date(2025, 9, 22)
INCOME = {"2025-07": 2500, "2025-08": 2500, "2025-09": 1833.33}


def build(**over):
    cfg = Config(**{"work_days": [4, 5, 6], "business_share_on_work_days": 0.85,
                    "prorate_partial_months": False, **over})
    normalise_config(cfg)
    return cfg


# ===========================================================================
group("A. Business only ever lands on a work day")
# ===========================================================================

for work_days in ([4, 5, 6], [0, 1, 2, 3, 4], [0, 6], list(range(7))):
    cfg = build(work_days=work_days)
    rows, summary = L.build_journeys(cfg, START, END, 0, 10000, INCOME)
    stray = [r for r in rows
             if r["purpose"] == "Business" and r["date"].weekday() not in work_days]
    check(f"work days {work_days}: no business anywhere else", not stray, len(stray))
    check(f"work days {work_days}: the totals still come out",
          sum(r["km"] for r in rows) == 10000)

# one day a week cannot hold this much, and says so rather than inventing a day
refused, message = refuses(L.build_journeys, build(work_days=[2]), START, END,
                           0, 10000, INCOME)
check("too few work days is refused, not fudged", refused)
check("and the refusal says what to change",
      "days worked" in message and "every single day" in message, message[:90])
roomy = build(work_days=[2], max_business_km_per_day=700, max_km_per_day=700)
check("raising the daily limit lets the same days carry it",
      sum(r["km"] for r in L.build_journeys(roomy, START, END, 0, 10000, INCOME)[0])
      == 10000)

cfg = build(work_days=[4, 5, 6])
rows, _s = L.build_journeys(cfg, START, END, 0, 10000, INCOME)
off_days = {r["date"] for r in rows if r["date"].weekday() not in (4, 5, 6)}
check("days off carry private travel only",
      all(r["purpose"] == "Private" for r in rows if r["date"] in off_days))
check("some days off do carry private travel", len(off_days) > 10, len(off_days))


# ===========================================================================
group("B. The share decides a work day's split")
# ===========================================================================

# with plenty of private travel about, the share is honoured closely
for share in (0.5, 0.7, 0.85, 0.95):
    cfg = build(business_share_on_work_days=share, max_private_km_per_day=400,
                max_km_per_day=900)
    rows, _s = L.build_journeys(cfg, START, END, 0, 24000, INCOME)
    work_rows = [r for r in rows if r["date"].weekday() in (4, 5, 6)]
    business = sum(r["km"] for r in work_rows if r["purpose"] == "Business")
    private = sum(r["km"] for r in work_rows if r["purpose"] == "Private")
    got = business / (business + private) if business + private else 0
    check(f"a share of {share:.0%} lands within 2 points", abs(got - share) < 0.02,
          f"got {got:.1%}")

# when there is barely any private travel, a work day simply reads as more business
cfg = build(business_share_on_work_days=0.5)
rows, _s = L.build_journeys(cfg, START, END, 0, 12000, INCOME)
work_rows = [r for r in rows if r["date"].weekday() in (4, 5, 6)]
business = sum(r["km"] for r in work_rows if r["purpose"] == "Business")
private = sum(r["km"] for r in work_rows if r["purpose"] == "Private")
got = business / (business + private)
check("a share is a target, not a promise to invent private travel", got > 0.5,
      f"got {got:.1%}")
check("and no private travel is conjured up",
      business + private <= 12000 and private <= 12000 - 6834)

cfg = build(business_share_on_work_days=1.0)
rows, _s = L.build_journeys(cfg, START, END, 0, 10000, INCOME)
work_private = [r for r in rows
                if r["purpose"] == "Private" and r["date"].weekday() in (4, 5, 6)]
check("a share of 100% keeps private travel off work days where it can",
      not work_private, len(work_private))


# ===========================================================================
group("C. Judging a pattern")
# ===========================================================================

fits = L.Pattern([4, 5, 6], 0.85, 350, 150, 420)
check("a workable pattern passes", L.assess(fits, START, END, 6834, 10000).ok)
check("and offers nothing to change", L.assess(fits, START, END, 6834, 10000).suggestion is None)

verdict = L.assess(fits, START, END, 14000, 20000)
check("too much business is caught", not verdict.ok)
check("and said in plain words", any("every one of them" in p for p in verdict.problems),
      verdict.problems)
check("a fix is offered", verdict.suggestion is not None)
check("the fix adds work days rather than cutting the claim",
      set(verdict.suggestion.work_days) >= set(fits.work_days)
      and verdict.suggestion.max_business_km_per_day >= fits.max_business_km_per_day)
check("the changes are explained", verdict.changes and all(isinstance(c, str)
                                                           for c in verdict.changes))

nowhere = L.Pattern([0], 0.85, 350, 150, 420)     # Mondays only
verdict = L.assess(nowhere, date(2025, 7, 1), date(2025, 7, 3), 5000, 6000)
check("a period with no work days in it is caught", not verdict.ok)

# a month can be crowded even when the whole period looks roomy
crowded = L.assess(fits.copy(work_days=[2]), START, END, 6834, 10000,
                   L.month_pressure_for({"2025-07": 2500, "2025-08": 2500,
                                         "2025-09": 1834}, START, END))
check("one crowded month is caught on its own", not crowded.ok)
check("and named", any("August 2025" in p for p in crowded.problems), crowded.problems)
check("with a fix that covers it", crowded.suggestion is not None)

check("private on work days from the share",
      L.private_on_work_days(8500, 0.85) == 1500)
check("a full share leaves none", L.private_on_work_days(8500, 1.0) == 0)
check("describe reads as a sentence", "work" in L.describe(fits).lower())


# ===========================================================================
group("D. Suggestions always work, over many random patterns")
# ===========================================================================

rng = random.Random(2026)
fine = fixed = impossible = faults = 0
for _ in range(4000):
    start = date(2025, 1, 1) + timedelta(days=rng.randint(0, 500))
    end = start + timedelta(days=rng.choice([13, 27, 55, 83, 92, 180, 364]))
    pattern = L.Pattern(sorted(rng.sample(range(7), rng.randint(1, 7))),
                        rng.choice([0.5, 0.7, 0.85, 0.95, 1.0]),
                        rng.choice([100, 250, 350]), rng.choice([50, 150, 300]),
                        rng.choice([200, 420, 500]))
    total = rng.randint(500, 60000)
    business = rng.randint(0, total)
    verdict = L.assess(pattern, start, end, business, total)
    if verdict.ok:
        fine += 1
        continue
    if verdict.suggestion is None:
        impossible += 1
        continue
    fixed += 1
    suggestion = verdict.suggestion
    if L.problems_with(suggestion, L.measure(suggestion, start, end, business, total)):
        faults += 1
    if not set(pattern.work_days) <= set(suggestion.work_days):
        faults += 1
    if suggestion.max_business_km_per_day < pattern.max_business_km_per_day:
        faults += 1
check(f"every suggestion fits and never shrinks the claim "
      f"({fine} already fine, {fixed} fixed, {impossible} beyond fixing)",
      faults == 0, faults)


# ===========================================================================
group("E. Patterns the engine has fixed can then be built")
# ===========================================================================

rng = random.Random(5)
built = refused = 0
for _ in range(200):
    start = date(2025, 1, 1) + timedelta(days=rng.randint(0, 300))
    end = start + timedelta(days=rng.choice([27, 55, 83, 92]))
    blocks = L.month_blocks(start, end)
    income = {k: rng.choice([0, 2000, 5000]) * used / length
              for k, _s, _e, used, length in blocks}
    business = L.business_by_month(income)
    _t, business_km = L.month_targets_from(business)
    if business_km == 0:
        continue
    total = business_km + rng.randint(0, 4000)
    cfg = build(work_days=sorted(rng.sample(range(7), rng.randint(1, 4))),
                business_share_on_work_days=rng.choice([0.6, 0.85, 1.0]),
                max_business_km_per_day=rng.choice([150, 350]),
                max_private_km_per_day=rng.choice([80, 150]),
                max_km_per_day=rng.choice([300, 420]))
    verdict = L.check_pattern(cfg, start, end, business, total)
    if not verdict.ok:
        if verdict.suggestion is None:
            refused += 1
            continue
        L.apply_to(cfg, verdict.suggestion)
        normalise_config(cfg)
    try:
        rows, summary = L.build_journeys(cfg, start, end, 1000, 1000 + total, business)
    except Exception as exc:                                   # noqa: BLE001
        check(f"a pattern the engine approved still builds", False,
              f"{type(exc).__name__}: {exc}")
        continue
    built += 1
    if sum(r["km"] for r in rows) != total:
        check("totals hold after a suggested fix", False)
    previous = 1000
    for row in rows:
        if row["odo_start"] != previous:
            check("the odometer chain holds after a suggested fix", False)
            break
        previous = row["odo_end"]
    stray = [r for r in rows if r["purpose"] == "Business"
             and r["date"].weekday() not in set(cfg.work_days)]
    if stray:
        check("business stays on work days after a suggested fix", False, len(stray))
check(f"every approved pattern built cleanly ({built} built, {refused} beyond fixing)",
      True)

report("Pattern")
