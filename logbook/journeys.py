"""Turning totals into a list of journeys.

The shape of a day, under the rules the driver gives:
  * a work day carries the business travel, and may carry private travel too
  * a day off carries private travel only - never business
  * business is written first on a day that holds both
"""

from __future__ import annotations

import random

from .allocate import allocate, lift_caps, month_targets_from, percentile
from .config import LONG_DAY_PERCENTILE, WORK_TYPES
from .dates import daterange, month_blocks
from .errors import fail
from .pattern import private_on_work_days


def assign_work_types(business_alloc: dict, work_type: str, rideshare_share: float,
                      rng: random.Random) -> dict:
    """Label each working day rideshare or delivery so the split lands close.

    One day carries one kind of work, which is how a driver would write it up;
    days go to whichever side is furthest behind its share.
    """
    days = sorted(d for d, km in business_alloc.items() if km > 0)
    if work_type == "rideshare":
        return {d: "rideshare" for d in days}
    if work_type == "delivery":
        return {d: "delivery" for d in days}

    total = sum(business_alloc[d] for d in days)
    want_ride = total * rideshare_share
    want_deliver = total - want_ride
    used_ride = used_deliver = 0.0
    out = {}
    for day in days:
        km = business_alloc[day]
        behind_ride = want_ride - used_ride
        behind_deliver = want_deliver - used_deliver
        if behind_ride > behind_deliver or (behind_ride == behind_deliver
                                            and rng.random() < 0.5):
            out[day] = "rideshare"
            used_ride += km
        else:
            out[day] = "delivery"
            used_deliver += km
    return out


def pick_destination(pool: list, km: int, long_day: int, rng: random.Random,
                     avoid: str = "") -> str:
    """Where the day's driving went.

    A long day names two areas, since one suburb would not match the distance,
    and the area just used is skipped so the column does not repeat itself.
    """
    if not pool:
        return ""
    choices = [d for d in pool if d != avoid] or list(pool)
    first = rng.choice(choices)
    if km >= long_day and len(pool) > 1:
        second = rng.choice([d for d in pool if d != first])
        return f"{first} / {second}"
    return first


def build_journeys(cfg, start, end, start_odo: int, end_odo: int,
                   business_by_month: dict):
    """Every journey between the two odometer readings, in date order."""
    rng = random.Random(cfg.seed)
    total_km = end_odo - start_odo
    month_targets, business_total = month_targets_from(business_by_month)
    private_total = total_km - business_total
    notes: list = []

    if business_total > total_km:
        fail(f"What you earned works out at {business_total:,} business km, but the "
             f"odometer readings only cover {total_km:,} km.")

    work_days = set(cfg.work_days)
    all_days = list(daterange(start, end))
    work_dates = [d for d in all_days if d.weekday() in work_days]
    off_dates = [d for d in all_days if d.weekday() not in work_days]
    min_km = max(0, min(cfg.min_journey_km, cfg.max_business_km_per_day,
                        cfg.max_private_km_per_day))

    if business_total > 0 and not work_dates:
        fail("None of the days you work fall inside this period, so there is nowhere "
             "to record business travel.")

    # --- business: work days only ------------------------------------------
    business_alloc: dict = {d: 0 for d in all_days}
    for key, month_start, month_end, _used, _length in month_blocks(start, end):
        target = month_targets.get(key, 0)
        if target <= 0:
            continue
        days = [d for d in daterange(month_start, month_end) if d.weekday() in work_days]
        if not days:
            fail(f"{month_start:%B %Y} has income against it but none of your work days "
                 f"fall in it. Add a day, or move the income to another month.")
        caps = {d: cfg.max_business_km_per_day for d in days}
        caps = lift_caps(target, days, caps, cfg.auto_cap_ceiling,
                         f"{month_start:%B %Y}", "business", notes)
        business_alloc.update(
            allocate(days, target, rng, caps, min_km, cfg.rest_day_chance))

    # --- private: the share decides how much shares a work day --------------
    private_alloc: dict = {d: 0 for d in all_days}
    if private_total > 0:
        wanted_here = private_on_work_days(business_total,
                                           cfg.business_share_on_work_days)
        wanted_here = min(wanted_here, private_total)
        room_elsewhere = len(off_dates) * cfg.max_private_km_per_day
        # whatever the days off cannot hold has to share a work day
        wanted_here = max(wanted_here, private_total - room_elsewhere)
        wanted_here = min(wanted_here, private_total)

        here_caps = {d: max(0, min(cfg.max_private_km_per_day,
                                   cfg.max_km_per_day - business_alloc.get(d, 0)))
                     for d in work_dates}
        if wanted_here > 0 and work_dates:
            here_caps = lift_caps(wanted_here, work_dates, here_caps,
                                  cfg.auto_cap_ceiling, "work days", "private", notes)
            room_here = sum(here_caps.values())
            wanted_here = min(wanted_here, room_here)
            private_alloc.update(allocate(work_dates, wanted_here, rng, here_caps,
                                          min_km, cfg.quiet_day_chance))

        remaining = private_total - sum(private_alloc.values())
        if remaining > 0:
            if not off_dates:
                fail("Every day is a work day and they cannot hold all the private "
                     "travel as well. Work fewer days, or raise the daily caps.")
            off_caps = {d: cfg.max_private_km_per_day for d in off_dates}
            off_caps = lift_caps(remaining, off_dates, off_caps, cfg.auto_cap_ceiling,
                                 "days off", "private", notes)
            for day, km in allocate(off_dates, remaining, rng, off_caps,
                                    min_km, cfg.quiet_day_chance).items():
                private_alloc[day] = private_alloc.get(day, 0) + km

    # --- write the rows -----------------------------------------------------
    work_type = cfg.work_type if cfg.work_type in WORK_TYPES else "rideshare"
    work_kinds = assign_work_types(business_alloc, work_type, cfg.rideshare_share, rng)
    reasons = {"rideshare": cfg.rideshare_reasons, "delivery": cfg.delivery_reasons}
    areas = {"rideshare": list(cfg.rideshare_destinations or []),
             "delivery": list(cfg.delivery_destinations or [])}
    long_day = percentile([v for v in business_alloc.values() if v > 0],
                          LONG_DAY_PERCENTILE)
    last_area = {"rideshare": "", "delivery": ""}

    rows, odo, number = [], start_odo, 0
    for day in all_days:
        legs = []
        business_km = business_alloc.get(day, 0)
        private_km = private_alloc.get(day, 0)
        if business_km > 0:                              # business is recorded first
            kind = work_kinds.get(day, "rideshare" if work_type == "both" else work_type)
            area = pick_destination(areas[kind], business_km, long_day, rng,
                                    last_area[kind])
            if area:
                last_area[kind] = area.split(" / ")[0]
            legs.append(("Business", business_km, rng.choice(reasons[kind]), kind, area))
        if private_km > 0:
            legs.append(("Private", private_km, rng.choice(cfg.private_reasons),
                         "private", ""))
        for purpose, km, reason, kind, area in legs:
            number += 1
            rows.append({"n": number, "date": day, "purpose": purpose, "reason": reason,
                         "destination": area, "work_type": kind,
                         "odo_start": odo, "odo_end": odo + km, "km": km})
            odo += km

    if odo != end_odo:
        raise AssertionError(f"Odometer mismatch: ended at {odo}, expected {end_odo}")

    summary = {"total_km": total_km, "business_km": business_total,
               "private_km": private_total, "journeys": len(rows),
               "business_pct": business_total / total_km if total_km else 0.0,
               "work_days_used": sum(1 for v in business_alloc.values() if v > 0),
               "work_type": work_type,
               "rideshare_km": sum(r["km"] for r in rows if r["work_type"] == "rideshare"),
               "delivery_km": sum(r["km"] for r in rows if r["work_type"] == "delivery"),
               "notes": notes}
    if len({r["reason"] for r in rows if r["purpose"] == "Business"}) < 2:
        notes.append("Every business journey carries the same reason. The ATO expects an "
                     "entry descriptive enough to characterise the journey and to match "
                     "its distance.")
    return rows, summary
