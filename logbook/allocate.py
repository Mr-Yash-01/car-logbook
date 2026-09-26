"""Spreading a total number of kilometres across days without losing one.

Every function here conserves its total exactly. That matters more than anything
else in the file: the odometer column has to run unbroken from the opening
reading to the closing one, so a kilometre dropped here shows up as a gap a tax
officer could ask about.
"""

from __future__ import annotations

import math
import random

from .errors import fail


def largest_remainder(weights: dict, total: int) -> dict:
    """Split a whole number in proportion to weights, exactly."""
    keys = list(weights)
    total = int(total)
    if not keys or total <= 0:
        return {k: 0 for k in keys}
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        weights = {k: 1.0 for k in keys}
        weight_sum = float(len(keys))
    raw = {k: weights[k] / weight_sum * total for k in keys}
    out = {k: int(math.floor(v)) for k, v in raw.items()}
    short = total - sum(out.values())
    order = sorted(keys, key=lambda k: (raw[k] - out[k], weights[k]), reverse=True)
    for i in range(short):
        out[order[i % len(order)]] += 1
    return out


def month_targets_from(business_by_month: dict):
    """Whole kilometres per month. A leftover fraction goes to business, not private."""
    raw_total = sum(max(float(v), 0.0) for v in business_by_month.values())
    total = int(math.ceil(raw_total - 1e-9))
    targets = largest_remainder(
        {k: max(float(v), 0.0) for k, v in business_by_month.items()}, total)
    return targets, total


def enforce_caps(alloc: dict, caps: dict) -> dict:
    alloc = dict(alloc)
    for _ in range(500):
        excess = sum(max(0, v - caps[k]) for k, v in alloc.items())
        if excess == 0:
            return alloc
        for k in alloc:
            alloc[k] = min(alloc[k], caps[k])
        room = {k: caps[k] - v for k, v in alloc.items() if v < caps[k]}
        if not room or sum(room.values()) < excess:
            fail("A daily cap is too low for the kilometres being recorded.")
        for k, v in largest_remainder(room, excess).items():
            alloc[k] += v
    return alloc


def enforce_min(alloc: dict, min_km: int, caps: dict) -> dict:
    """Fold away trips too small to be worth recording, without losing a kilometre.

    A day is only emptied once the others are known to have room for all of it.
    """
    if min_km <= 0:
        return alloc
    alloc = dict(alloc)
    leave_alone = set()
    for _ in range(1000):
        smalls = [k for k, v in alloc.items() if 0 < v < min_km and k not in leave_alone]
        if not smalls:
            return alloc
        k = smalls[0]
        amount = alloc[k]
        recipients = [x for x, v in alloc.items() if x != k and min_km <= v < caps[x]]
        if sum(caps[x] - alloc[x] for x in recipients) < amount:
            leave_alone.add(k)      # nowhere to put it, so the day keeps its distance
            continue
        alloc[k] = 0
        i = 0
        while amount > 0:
            r = recipients[i % len(recipients)]
            if alloc[r] < caps[r]:
                alloc[r] += 1
                amount -= 1
            i += 1
    return alloc


def allocate(days: list, total: int, rng: random.Random,
             caps: dict, min_km: int, rest_chance: float) -> dict:
    """Spread `total` over `days`, varying day to day, never exceeding each day's cap."""
    result = {d: 0 for d in days}
    total = int(round(total))
    if total <= 0 or not days:
        return result
    capacity = sum(caps[d] for d in days)
    if total > capacity:
        fail(f"{total:,} km cannot fit in {len(days)} day(s) holding at most "
             f"{capacity:,} km.")

    usable = [d for d in days if caps[d] > 0]
    active = [d for d in usable if rng.random() >= rest_chance] or list(usable)
    if min_km > 0:
        most = max(1, min(len(usable), total // min_km))
        if len(active) > most:
            active = rng.sample(active, most)
    spare = [d for d in usable if d not in set(active)]
    rng.shuffle(spare)
    while sum(caps[d] for d in active) < total and spare:
        active.append(spare.pop())

    alloc = largest_remainder({d: rng.uniform(0.55, 1.45) * caps[d] for d in active}, total)
    caps_active = {d: caps[d] for d in active}
    alloc = enforce_caps(alloc, caps_active)
    alloc = enforce_min(alloc, min_km, caps_active)
    result.update(alloc)
    if sum(result.values()) != total:
        raise AssertionError(f"allocation lost kilometres: {sum(result.values())} of {total}")
    return result


def lift_caps(target: int, days: list, caps: dict, ceiling: int,
              where: str, kind: str, notes: list) -> dict:
    """Raise per-day room when a stretch genuinely needs it; refuse the impossible."""
    target = int(round(target))
    caps = dict(caps)
    if not days or target <= sum(caps[d] for d in days):
        return caps
    needed = math.ceil(target / len(days))
    if needed <= ceiling:
        notes.append(f"{where}: {target:,} {kind} km over {len(days)} day(s) needs up to "
                     f"{needed:,} km in a day - daily room lifted for that stretch.")
        for d in days:
            caps[d] = max(caps[d], needed)
        return caps
    fail(f"{where} needs {target:,} {kind} km across only {len(days)} day(s) - about "
         f"{needed:,} km every single day.\n"
         f"  Change one of these:\n"
         f"    - the income entered for {where}\n"
         f"    - the days worked, so there are more of them\n"
         f"    - the length of the logbook period")


def percentile(values: list, fraction: float) -> int:
    """Nearest-rank percentile; 0 for an empty list."""
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[idx]
