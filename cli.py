#!/usr/bin/env python3
"""Car logbook generator - the question-by-question tool.

    python cli.py                            # asks for everything
    python cli.py --config inputs.json       # no questions
    python cli.py --config inputs.json --downloads --open
    python cli.py --write-config-template inputs.json

Every question explains what it is for and shows an example. Business kilometres
come from what you earned; there is nothing to set and nothing to get wrong.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logbook as L                                      # noqa: E402
from logbook import questions as Q                       # noqa: E402
from logbook.config import Config, normalise_config      # noqa: E402
from logbook.errors import LogbookError                  # noqa: E402
from logbook.wording import city_names                   # noqa: E402


# ---------------------------------------------------------------------------
# Asking
# ---------------------------------------------------------------------------

def explain(key: str):
    """Print the reason for a question before asking it."""
    print(f"\n  {Q.why(key)}")


def _read(label: str, default=None) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    while True:
        try:
            raw = input(f"{label}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nCancelled - nothing was written.")
        if raw:
            return raw
        if default is not None:
            return str(default)
        print("  ! An answer is needed.")


def ask(key: str, default=None) -> str:
    explain(key)
    return _read(f"{Q.ask_text(key)} (e.g. {Q.example(key)})", default)


def ask_checked(key: str, default, cleaner, **kw):
    """Ask until the answer passes its own format check."""
    explain(key)
    label = f"{Q.ask_text(key)} (e.g. {Q.example(key)})"
    while True:
        try:
            return cleaner(_read(label, default), **kw)
        except LogbookError as exc:
            print(f"  ! {exc}")


def ask_number(key: str, default=None, **kw):
    explain(key)
    label = f"{Q.ask_text(key)} (e.g. {Q.example(key)})"
    while True:
        try:
            return L.parse_amount(_read(label, default), Q.ask_text(key), **kw)
        except LogbookError as exc:
            print(f"  ! {exc}")


def ask_yes_no(label: str, default=True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        try:
            raw = input(f"{label} [{hint}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nCancelled - nothing was written.")
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  ! Please answer y or n.")


def ask_choice(label: str, options: list, default: int = 0) -> str:
    for i, (_value, text) in enumerate(options, start=1):
        print(f"    {i}) {text}")
    numbers = [str(i) for i in range(1, len(options) + 1)]
    while True:
        picked = _read(f"{label} ({'/'.join(numbers)})", str(default + 1))
        if picked in numbers:
            return options[int(picked) - 1][0]
        print(f"  ! Enter a number from 1 to {len(options)}.")


def ask_list(key: str, default: list) -> list:
    explain(key)
    raw = _read(f"{Q.ask_text(key)}, separated by | (e.g. {Q.example(key)})",
                " | ".join(default))
    return L.clean_wordings([p.strip() for p in raw.split("|")], default)


def ask_date(key: str, default=None) -> date:
    explain(key)
    label = f"{Q.ask_text(key)} DD/MM/YYYY (e.g. {Q.example(key)})"
    while True:
        value = L.parse_date(_read(label, default))
        if value and L.MIN_YEAR <= value.year <= L.MAX_YEAR:
            return value
        print(f"  ! Could not read that as a date between {L.MIN_YEAR} and {L.MAX_YEAR}.")


# ---------------------------------------------------------------------------
# The conversation
# ---------------------------------------------------------------------------

def period_step(cfg: Config):
    print("\n--- 1. The period the logbook covers ---")
    today = date.today()
    default_start = date(today.year if today.month >= 7 else today.year - 1, 7, 1)
    while True:
        start = ask_date("start_date", default_start.strftime("%d/%m/%Y"))
        weeks = int(ask_number("weeks", 12, minimum=1, maximum=104))
        end = start + timedelta(weeks=weeks, days=-1)
        days = (end - start).days + 1
        print(f"  -> {start:%d %b %Y} to {end:%d %b %Y} ({days} days)")
        if days < 84:
            print("  * That is under 12 weeks. A first logbook needs 12 continuous "
                  "weeks; a shorter one still generates.")
        if L.spans_financial_years(start, end):
            years = [label for label, _a, _b in L.financial_years_in(start, end)]
            print(f"  * It crosses 30 June, covering {', '.join(years)}.")
        if ask_yes_no("  Use that period?", True):
            cfg.start_date, cfg.end_date = start.isoformat(), end.isoformat()
            return start, end


def sheet_mode_step(cfg: Config, start: date, end: date):
    if not L.spans_financial_years(start, end):
        cfg.sheet_mode = "combined"
        return
    print("\n--- 2. How to lay it out ---")
    explain("sheet_mode")
    years = [label for label, _a, _b in L.financial_years_in(start, end)]
    cfg.sheet_mode = ask_choice(
        "  Choose",
        [("per-year", f"A separate sheet for each year ({', '.join(years)})"),
         ("combined", "One sheet covering the whole period")], default=0)


def income_step(cfg: Config, start: date, end: date):
    print("\n--- 3. What you earned ---")
    blocks = L.month_blocks(start, end)
    flat = None
    if len(blocks) > 1:
        explain("income_same")
        if ask_yes_no(f"  Did you earn about the same each month "
                      f"(all {len(blocks)} of them)?", False):
            flat = ask_number("income_month", 5000, minimum=0)
    income = {}
    for key, month_start, month_end, used, length in blocks:
        part = used < length
        if flat is not None:
            amount = flat * used / length if part else flat
            if part:
                print(f"  {month_start:%B %Y} has {length} days and the period covers "
                      f"{used} -> ${amount:,.2f}")
        else:
            if part:
                label = (f"Income for {month_start:%d %b}-{month_end:%d %b %Y}, "
                         f"{used} of the {length} days in {month_start:%B %Y} ($)")
            else:
                label = f"Income for {month_start:%B %Y}, all {length} days ($)"
            if not income:
                explain("income_month")
            amount = L.parse_amount(_read(label, 5000), "Income", minimum=0)
        income[key] = float(amount)
    cfg.prorate_partial_months = False        # each figure is already for its stretch
    cfg.monthly_income = income

    business = L.business_by_month(income)
    targets, total = L.month_targets_from(business)
    print("\n  Month             Days used    Income          Business km")
    print("  " + "-" * 58)
    for key, month_start, _me, used, length in blocks:
        print(f"  {month_start:%B %Y:<17} {used:>2} of {length:<2}    "
              f"${income[key]:>10,.2f}    {targets.get(key, 0):>7,}")
    print("  " + "-" * 58)
    print(f"  {'Total':<17} {sum(b[3] for b in blocks):>5}       "
          f"${sum(income.values()):>10,.2f}    {total:>7,}")
    return total


def vehicle_step(cfg: Config):
    print("\n--- 4. Your car ---")
    cfg.owner_name = ask_checked("owner_name", "", L.clean_person)
    cfg.abn = ask_checked("abn", "", L.clean_abn)
    cfg.make = ask_checked("make", cfg.make, L.clean_vehicle_word, label="make")
    cfg.model = ask_checked("model", cfg.model, L.clean_vehicle_word, label="model")
    cfg.year_of_manufacture = ask_checked("year_of_manufacture", "", L.clean_year)
    cfg.engine_capacity = ask_checked("engine_capacity", cfg.engine_capacity,
                                      L.clean_engine)
    cfg.registration = ask_checked("registration", cfg.registration,
                                   L.clean_registration)


def odometer_step(cfg: Config, start: date, end: date):
    print("\n--- 5. Odometer readings ---")
    days = (end - start).days + 1
    while True:
        start_odo = ask_checked("start_odometer", 45230, L.clean_odometer,
                                label="The start reading")
        end_odo = ask_checked("end_odometer", None, L.clean_odometer,
                              label="The end reading")
        if end_odo <= start_odo:
            print(f"  ! The end reading has to be higher than {start_odo:,}.")
            continue
        total = end_odo - start_odo
        per_day = total / days
        print(f"  -> {total:,} km over {days} days, about {per_day:,.0f} km a day")
        if per_day > L.PLAUSIBLE_DAILY_KM and not ask_yes_no("  Is that right?", False):
            continue
        if per_day < 1 and not ask_yes_no("  Is that right?", False):
            continue
        cfg.start_odometer, cfg.end_odometer = start_odo, end_odo
        return start_odo, end_odo


def work_type_step(cfg: Config):
    print("\n--- 6. What the driving is for ---")
    explain("work_type")
    cfg.work_type = ask_choice("  Choose",
                               [("rideshare", "Rideshare"),
                                ("delivery", "Delivery driving"),
                                ("both", "Both")], default=0)


def pattern_step(cfg: Config, start: date, end: date, business_km: int, total_km: int):
    print("\n--- 7. How you drive ---")
    while True:
        cfg.work_days = L.parse_days(ask("work_days", "Fri,Sat,Sun"), cfg.work_days)
        print(f"  -> {L.name_days(cfg.work_days)}. Business travel goes on these days "
              f"only; the rest carry private travel.")
        cfg.business_share_on_work_days = L.parse_share(
            ask("business_share_on_work_days", 85), "The business share")
        cfg.max_km_per_day = int(ask_number("max_km_per_day", 420, minimum=1))
        cfg.max_business_km_per_day = int(
            ask_number("max_business_km_per_day", 350, minimum=1))
        cfg.max_private_km_per_day = int(
            ask_number("max_private_km_per_day", 150, minimum=1))
        cfg.seed = int(ask_number("seed", 42))

        for message in normalise_config(cfg):
            print(f"  * {message}")
        verdict = L.assess(L.pattern_from(cfg), start, end, business_km, total_km,
                           L.month_pressure_for(
                               L.business_by_month(cfg.monthly_income), start, end))
        if verdict.ok:
            print("  -> That pattern fits.")
            return
        print("\n  That pattern will not hold these kilometres:")
        for problem in verdict.problems:
            print(f"    - {problem}")
        if verdict.suggestion is None:
            print("  Nothing close to it works. Try more work days, a longer period, "
                  "or check the income and odometer figures.")
            continue
        print("\n  The closest fit that still claims every business kilometre:")
        for change in verdict.changes:
            print(f"    - {change}")
        print(f"    {L.describe(verdict.suggestion)}")
        if ask_yes_no("  Use that?", True):
            L.apply_to(cfg, verdict.suggestion)
            normalise_config(cfg)
            return
        print("  Fair enough - let's set the pattern again.")


def wording_step(cfg: Config):
    print("\n--- 8. How each row reads ---")
    explain("city")
    cfg.city = _read(f"{Q.ask_text('city')} ({', '.join(city_names())})", cfg.city).lower()
    normalise_config(cfg)
    if cfg.work_type in ("rideshare", "both"):
        cfg.rideshare_reasons = ask_list("rideshare_reasons", cfg.rideshare_reasons)
    if cfg.work_type in ("delivery", "both"):
        cfg.delivery_reasons = ask_list("delivery_reasons", cfg.delivery_reasons)
    cfg.private_reasons = ask_list("private_reasons", cfg.private_reasons)
    areas = ask_list("destinations", cfg.rideshare_destinations)
    cfg.rideshare_destinations = areas
    cfg.delivery_destinations = (areas if cfg.work_type != "both"
                                 else cfg.delivery_destinations)


def output_step(cfg: Config):
    print("\n--- 9. The file ---")
    if cfg.sheet_mode == "combined":
        cfg.sheet_name = ask("sheet_name", cfg.sheet_name)
    name = ask("output", cfg.output)
    if not name.lower().endswith(".xlsx"):
        name += ".xlsx"
    if not Path(name).parent.name and not Path(name).is_absolute():
        folder = downloads_dir()
        if folder and ask_yes_no(f"  Save it to {folder}?", True):
            name = str(folder / Path(name).name)
    cfg.output = name


def collect() -> Config:
    cfg = Config()
    print("\n" + "=" * 70)
    print(" CAR LOGBOOK GENERATOR")
    print("=" * 70)
    print(" Each question explains itself. Press Enter to take the value in [brackets].")

    start, end = period_step(cfg)
    sheet_mode_step(cfg, start, end)
    business_km = income_step(cfg, start, end)
    vehicle_step(cfg)
    start_odo, end_odo = odometer_step(cfg, start, end)
    if business_km > end_odo - start_odo:
        print(f"\n  ! What you earned works out at {business_km:,} business km, more "
              f"than the {end_odo - start_odo:,} km between your readings.")
        extra = int(L.parse_amount(
            _read("  Private kilometres to add on top (e.g. 500)", 500),
            "The private kilometres", minimum=0))
        cfg.end_odometer = start_odo + business_km + extra
        print(f"  -> End reading raised to {cfg.end_odometer:,} km so it fits, with "
              f"{extra} km of private travel on top.")
        end_odo = cfg.end_odometer
    work_type_step(cfg)
    pattern_step(cfg, start, end, business_km, end_odo - start_odo)
    wording_step(cfg)
    output_step(cfg)
    return cfg


# ---------------------------------------------------------------------------
# Handing the file over
# ---------------------------------------------------------------------------

def downloads_dir():
    home = Path.home()
    user_dirs = home / ".config" / "user-dirs.dirs"
    if user_dirs.exists():
        try:
            for line in user_dirs.read_text().splitlines():
                if line.startswith("XDG_DOWNLOAD_DIR"):
                    raw = line.split("=", 1)[1].strip().strip('"')
                    candidate = Path(raw.replace("$HOME", str(home)))
                    if candidate.is_dir():
                        return candidate
        except OSError:
            pass
    candidate = home / "Downloads"
    return candidate if candidate.is_dir() else None


def open_file(path) -> bool:
    try:
        if sys.platform.startswith("darwin"):
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(str(path))                      # noqa: S606
        else:
            subprocess.run(["xdg-open", str(path)], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:                                    # noqa: BLE001
        return False


def deliver(target, interactive: bool, auto_open: bool):
    full = Path(target).resolve()
    print(f"\n  File: {full}")
    if auto_open or (interactive and ask_yes_no("  Open it now?", True)):
        if not open_file(full):
            print("  Could not open it here - the path above is the file.")


def main():
    parser = argparse.ArgumentParser(description="Generate a car logbook spreadsheet.")
    parser.add_argument("-o", "--output", help="output .xlsx path")
    parser.add_argument("-c", "--config", help="JSON config file, skips the questions")
    parser.add_argument("--write-config-template", metavar="PATH",
                        help="write a starter JSON config and exit")
    parser.add_argument("--seed", type=int, help="override the shuffle number")
    parser.add_argument("--downloads", action="store_true",
                        help="save into your Downloads folder")
    parser.add_argument("--open", dest="open_after", action="store_true",
                        help="open the workbook once it is written")
    args = parser.parse_args()

    if args.write_config_template:
        path = L.write_config_template(args.write_config_template)
        print(f"Template written to {path}. Edit it, then run: python cli.py -c {path}")
        return

    interactive = not args.config
    try:
        if args.config:
            cfg = L.config_from(__import__("json").load(open(args.config)))
        else:
            cfg = collect()
    except LogbookError as exc:
        sys.exit(f"  ! {exc}")
    except (OSError, ValueError) as exc:
        sys.exit(f"  ! Could not read {args.config}: {exc}")

    if args.seed is not None:
        cfg.seed = args.seed
    out_path = args.output or cfg.output
    if args.downloads:
        folder = downloads_dir()
        if folder:
            out_path = str(folder / Path(out_path).name)

    try:
        result = L.generate(cfg)
    except LogbookError as exc:
        sys.exit(f"\n  ! {exc}")

    for message in result["notes"]:
        print(f"  * {message}")
    summary = result["summary"]
    if interactive:
        print(f"\n  Ready: {summary['journeys']} journeys, "
              f"{summary['business_km']:,} business km of {summary['total_km']:,} "
              f"({summary['business_pct']:.1%}).")
        if not ask_yes_no("  Write the file now?", True):
            sys.exit("  Nothing written.")

    target = Path(out_path)
    if target.suffix.lower() != ".xlsx":
        target = target.with_suffix(".xlsx")
    target.write_bytes(result["bytes"])

    print("\n" + "=" * 70)
    print(" Logbook written")
    print("=" * 70)
    print(f"  Period        {summary['start']:%d/%m/%Y} - {summary['end']:%d/%m/%Y}"
          f"  ({summary['days']} days)")
    print(f"  Odometer      {summary['start_odometer']:,} -> "
          f"{summary['end_odometer']:,} km")
    print(f"  Total         {summary['total_km']:,} km")
    print(f"  Business      {summary['business_km']:,} km across "
          f"{summary['work_days_used']} work days")
    if summary["work_type"] == "both":
        print(f"    rideshare   {summary['rideshare_km']:,} km")
        print(f"    delivery    {summary['delivery_km']:,} km")
    print(f"  Private       {summary['private_km']:,} km")
    print(f"  Business use  {summary['business_pct']:.1%}")
    print(f"  Journeys      {summary['journeys']} rows")
    print(f"  Sheets        {', '.join(result['sheets'])}")
    for message in result["warnings"]:
        print(f"  ! {message}")
    deliver(target, interactive, args.open_after)
    print()


if __name__ == "__main__":
    main()
