"""Can this travel pattern actually hold these kilometres, and if not, what would?

The rule the suggestions follow: never solve a problem by recording fewer
business kilometres. Business distance comes from what was earned, and cutting it
would quietly cut what can be claimed. So a pattern that does not fit is fixed by
working more days or lifting a daily cap - never by moving business kilometres
into private travel.

What the percentage is, is set by income and the odometer. Nothing here changes
it; this only decides whether the days can carry it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date

from .dates import DAY_NAMES, count_weekdays, name_days

# Days to try adding first when the work days cannot hold the business kilometres:
# the weekend and the end of the week, which is when most drivers pick up shifts.
DAY_PREFERENCE = [4, 5, 6, 3, 2, 1, 0]
CAP_CEILING = 600          # a day above this stops being believable


@dataclass
class Pattern:
    """The part of the settings this engine reasons about."""
    work_days: list
    business_share_on_work_days: float
    max_business_km_per_day: int
    max_private_km_per_day: int
    max_km_per_day: int

    def copy(self, **changes) -> "Pattern":
        return replace(self, **changes)


@dataclass
class Assessment:
    ok: bool
    problems: list                 # plain sentences, worst first
    changes: list                  # what the suggestion alters, in plain words
    suggestion: Pattern | None     # a pattern that fits, or None when nothing does
    facts: dict                    # the numbers behind the verdict


def pattern_from(cfg) -> Pattern:
    return Pattern(work_days=list(cfg.work_days),
                   business_share_on_work_days=float(cfg.business_share_on_work_days),
                   max_business_km_per_day=int(cfg.max_business_km_per_day),
                   max_private_km_per_day=int(cfg.max_private_km_per_day),
                   max_km_per_day=int(cfg.max_km_per_day))


def apply_to(cfg, pattern: Pattern):
    cfg.work_days = list(pattern.work_days)
    cfg.business_share_on_work_days = pattern.business_share_on_work_days
    cfg.max_business_km_per_day = pattern.max_business_km_per_day
    cfg.max_private_km_per_day = pattern.max_private_km_per_day
    cfg.max_km_per_day = pattern.max_km_per_day
    return cfg


def private_on_work_days(business_km: int, share: float) -> int:
    """How much private travel sits on work days, given the share of those days that is business."""
    if share >= 1.0:
        return 0
    if share <= 0:
        return 0
    return int(round(business_km * (1.0 - share) / share))


def month_pressure(pattern: Pattern, months) -> list:
    """Per month: how many work days it has, and how much business it must carry.

    Kilometres are allocated a month at a time, so a pattern that looks fine over
    the whole period can still leave one month with nowhere to put its income.
    """
    out = []
    for label, first, last, target in (months or []):
        if target <= 0:
            continue
        work_days = count_weekdays(first, last, pattern.work_days)
        out.append({"label": label, "work_days": work_days, "target": int(target),
                    "room": work_days * pattern.max_business_km_per_day})
    return out


def measure(pattern: Pattern, start: date, end: date,
            business_km: int, total_km: int, months=None) -> dict:
    """The numbers that decide whether a pattern works."""
    work_count = count_weekdays(start, end, pattern.work_days)
    period_days = (end - start).days + 1
    other_count = period_days - work_count
    private_km = max(0, total_km - business_km)

    business_room = work_count * pattern.max_business_km_per_day
    wanted_private_here = private_on_work_days(business_km, pattern.business_share_on_work_days)
    wanted_private_here = min(wanted_private_here, private_km)

    # A work day's private travel also has to fit under the day's overall ceiling,
    # alongside the business kilometres already on it.
    business_per_work_day = (business_km / work_count) if work_count else 0
    headroom_each = max(0, min(pattern.max_private_km_per_day,
                               pattern.max_km_per_day - math.ceil(business_per_work_day)))
    private_room_here = work_count * headroom_each
    private_room_elsewhere = other_count * pattern.max_private_km_per_day

    return {"months": month_pressure(pattern, months),
            "work_days": work_count, "other_days": other_count, "period_days": period_days,
            "business_km": business_km, "private_km": private_km, "total_km": total_km,
            "business_room": business_room,
            "private_here_wanted": wanted_private_here,
            "private_room_here": private_room_here,
            "private_room_elsewhere": private_room_elsewhere,
            "business_per_work_day": business_per_work_day}


def problems_with(pattern: Pattern, facts: dict) -> list:
    """Plain sentences naming what does not fit, worst first."""
    out = []
    if facts["work_days"] == 0:
        out.append("No day of the week you chose falls inside the period, so there is "
                   "nowhere to record business travel.")
        return out
    if facts["business_km"] > facts["business_room"]:
        need = math.ceil(facts["business_km"] / facts["work_days"])
        out.append(f"{facts['business_km']:,} business km across {facts['work_days']} work "
                   f"days is {need:,} km every one of them, above the "
                   f"{pattern.max_business_km_per_day:,} km cap.")
    if facts["business_per_work_day"] > pattern.max_km_per_day:
        out.append(f"Business alone comes to {facts['business_per_work_day']:,.0f} km on a "
                   f"work day, above the {pattern.max_km_per_day:,} km daily total.")

    for month in facts.get("months", []):
        if month["work_days"] == 0:
            out.append(f"{month['label']} has income against it but none of your work "
                       f"days fall in it.")
        elif month["target"] > month["room"]:
            need = math.ceil(month["target"] / month["work_days"])
            out.append(f"{month['label']} alone needs {month['target']:,} business km "
                       f"across {month['work_days']} work days - {need:,} km each, above "
                       f"the {pattern.max_business_km_per_day:,} km cap.")

    private_fits = facts["private_room_here"] + facts["private_room_elsewhere"]
    if facts["private_km"] > private_fits:
        out.append(f"{facts['private_km']:,} private km has nowhere to go: the days can "
                   f"hold about {private_fits:,} km.")
    elif facts["other_days"] == 0 and facts["private_km"] > facts["private_room_here"]:
        out.append("Every day is a work day, so all the private travel has to share those "
                   "days, and there is not enough room on them.")
    else:
        spill = facts["private_km"] - facts["private_here_wanted"]
        if spill > facts["private_room_elsewhere"]:
            out.append(f"Only {facts['private_room_elsewhere']:,} km of private travel fits "
                       f"on your days off, leaving {spill - facts['private_room_elsewhere']:,} "
                       f"km with nowhere to sit.")
    return out


def _fits(pattern: Pattern, start, end, business_km, total_km, months=None) -> bool:
    return not problems_with(pattern, measure(pattern, start, end, business_km,
                                              total_km, months))


def assess(pattern: Pattern, start: date, end: date,
           business_km: int, total_km: int, months=None) -> Assessment:
    """Judge a pattern and, when it does not fit, work out one that does.

    `months` is [(label, first day, last day, business km)] - pass it so a single
    crowded month is caught here rather than when the rows are built.
    """
    facts = measure(pattern, start, end, business_km, total_km, months)
    problems = problems_with(pattern, facts)
    if not problems:
        return Assessment(True, [], [], None, facts)

    trial, changes = pattern.copy(), []

    # 1. More work days first: it keeps every daily figure believable and never
    #    touches how much of the driving is business.
    if business_km > 0:
        for day in DAY_PREFERENCE:
            checked = measure(trial, start, end, business_km, total_km, months)
            crowded = any(m["work_days"] == 0 or m["target"] > m["room"]
                          for m in checked["months"])
            if (checked["work_days"] > 0 and not crowded
                    and business_km <= checked["business_room"]
                    and checked["business_per_work_day"] <= trial.max_km_per_day):
                break
            if day in trial.work_days:
                continue
            added = sorted(trial.work_days + [day])
            if count_weekdays(start, end, added) > checked["work_days"]:
                trial = trial.copy(work_days=added)
                changes.append(f"work {DAY_NAMES[day]}s as well")

    # 2. Then lift the business cap, if the days still cannot hold it.
    checked = measure(trial, start, end, business_km, total_km, months)
    tightest = max((math.ceil(m["target"] / m["work_days"])
                    for m in checked["months"] if m["work_days"]), default=0)
    if checked["work_days"] and (business_km > checked["business_room"]
                                 or tightest > trial.max_business_km_per_day):
        needed = max(tightest, math.ceil(business_km / checked["work_days"]))
        if needed <= CAP_CEILING:
            trial = trial.copy(max_business_km_per_day=needed,
                               max_km_per_day=max(trial.max_km_per_day, needed))
            changes.append(f"allow up to {needed:,} business km in a day")
        else:
            return Assessment(False, problems, [], None, facts)

    if trial.max_km_per_day < trial.max_business_km_per_day:
        trial = trial.copy(max_km_per_day=trial.max_business_km_per_day)

    # 3. Now the private side. The share decides how much private travel sits on
    #    work days; move it until the rest fits on the days off.
    checked = measure(trial, start, end, business_km, total_km, months)
    private_km, elsewhere = checked["private_km"], checked["private_room_elsewhere"]
    if private_km > elsewhere and business_km > 0:
        must_sit_here = private_km - elsewhere
        share = business_km / (business_km + must_sit_here)
        share = max(0.05, min(1.0, math.floor(share * 100) / 100))
        if abs(share - trial.business_share_on_work_days) > 0.005:
            trial = trial.copy(business_share_on_work_days=share)
            changes.append(f"count {share:.0%} of a work day as business, so the rest of "
                           f"your private travel fits on it")

    # 4. Last resort: raise the private cap so the kilometres have somewhere to sit.
    checked = measure(trial, start, end, business_km, total_km, months)
    if problems_with(trial, checked):
        spread_over = max(1, checked["work_days"] + checked["other_days"])
        needed = math.ceil(private_km / spread_over)
        if needed > trial.max_private_km_per_day and needed <= CAP_CEILING:
            trial = trial.copy(max_private_km_per_day=needed,
                               max_km_per_day=max(trial.max_km_per_day,
                                                  trial.max_business_km_per_day + needed))
            changes.append(f"allow up to {needed:,} private km in a day")

    if _fits(trial, start, end, business_km, total_km, months):
        return Assessment(False, problems, changes, trial, facts)
    return Assessment(False, problems, [], None, facts)


def describe(pattern: Pattern) -> str:
    """One line a person can read back."""
    return (f"work {name_days(pattern.work_days)}; "
            f"{pattern.business_share_on_work_days:.0%} of a work day is business; "
            f"at most {pattern.max_business_km_per_day:,} business and "
            f"{pattern.max_private_km_per_day:,} private km in a day, "
            f"{pattern.max_km_per_day:,} km all up")
