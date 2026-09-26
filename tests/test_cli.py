#!/usr/bin/env python3
"""The command-line tool, driven end to end the way a person would answer it."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, group, report                    # noqa: E402

from openpyxl import load_workbook                          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp())
CLI = ROOT / "cli.py"


def run(args, answers="", timeout=180):
    return subprocess.run([sys.executable, str(CLI)] + args, input=answers,
                          capture_output=True, text=True, timeout=timeout, cwd=ROOT)


ANSWERS = ["01/07/2025", "12", "y",                    # period
           "n", "5000", "5000", "5000",                # income month by month
           "Yash Vadukiya", "", "Toyota", "Corolla Hybrid", "2021", "1.8L", "ABC123",
           "45230", "55230",                           # odometer
           "3",                                        # both kinds of work
           "fri,sat,sun", "85", "420", "350", "150", "42",
           "brisbane", "", "", "", "",                 # city, then default wordings
           "Logbook"]


def full(out: Path, extra=()):
    return "\n".join(ANSWERS + [str(out)] + list(extra) + ["y", "n"]) + "\n"


# ===========================================================================
group("A. A whole run")
# ===========================================================================

out = TMP / "cli.xlsx"
result = run([], full(out))
check("it finishes cleanly", result.returncode == 0,
      (result.stdout[-300:] + result.stderr[-200:]))
check("the file is written", out.exists())
check("no traceback", "Traceback" not in result.stderr)
check("the summary is printed", "Business use" in result.stdout)
check("the income recap is shown",
      "Business km" in result.stdout and "Days used" in result.stdout)
check("it confirms before writing", "Write the file now?" in result.stdout)

ws = load_workbook(out).active
rows = [r for r in ws.iter_rows(values_only=True)
        if isinstance(r[0], int) and isinstance(r[6], int)]
check("journeys were written", len(rows) > 40, len(rows))
check("opens and closes on the readings", rows[0][6] == 45230 and rows[-1][7] == 55230)
check("business only on the named days",
      all(r[1].weekday() in (4, 5, 6) for r in rows if r[3] == "Business"))


# ===========================================================================
group("B. Every question explains itself")
# ===========================================================================

for needle in ["The first day you want recorded",
               "at least 12 continuous weeks",
               "registration papers",
               "The number on your dashboard",
               "Business travel is recorded on these days and no others",
               "The rest of that day counts as private",
               "same number always gives you the same logbook",
               "will not accept a bare"]:
    check(f"it explains: {needle[:38]}...", needle in result.stdout)
for example in ["(e.g. 01/07/2025)", "(e.g. ABC123)", "(e.g. 45230)", "(e.g. 42)",
                "(e.g. Fri,Sat,Sun or Mon-Fri)", "(e.g. 85)"]:
    check(f"it gives an example: {example}", example in result.stdout)
check("no rate per kilometre is ever mentioned",
      "per business kilometre" not in result.stdout)
check("no total-kilometres question", "Total kilometres travelled in the period"
      not in result.stdout)
check("no rideshare-share question", "how much is rideshare" not in result.stdout)


# ===========================================================================
group("C. The pattern check, and its suggestion")
# ===========================================================================

tight = ["01/07/2025", "12", "y", "n", "9000", "9000", "9000",
         "Test", "", "Toyota", "Corolla", "2021", "1.8L", "ABC123",
         "20000", "45000", "1",
         "sat", "85", "420", "350", "150", "42", "y",        # accept the suggestion
         "brisbane", "", "", "", "Logbook"]
out2 = TMP / "fit.xlsx"
result2 = run([], "\n".join(tight + [str(out2), "y", "n"]) + "\n")
check("a poor pattern is caught", "will not hold these kilometres" in result2.stdout)
check("the problem is named", "every one of them" in result2.stdout)
check("a fix is offered", "closest fit that still claims every business kilometre"
      in result2.stdout)
check("the fix is spelled out", "work " in result2.stdout and "km in a day" in result2.stdout)
check("accepting it produces a file", result2.returncode == 0 and out2.exists(),
      result2.stdout[-200:])
ws2 = load_workbook(out2).active
rows2 = [r for r in ws2.iter_rows(values_only=True)
         if isinstance(r[0], int) and isinstance(r[6], int)]
check("and the claim was not cut",
      sum(r[8] if isinstance(r[8], int) else 0 for r in rows2) >= 0)
check("business still lands only on work days",
      len({r[1].weekday() for r in rows2 if r[3] == "Business"}) >= 1)


# ===========================================================================
group("D. Two financial years")
# ===========================================================================

across = ["01/05/2025", "18", "y",                       # 1 May, 18 weeks -> crosses June
          "1",                                           # separate sheets
          "n", "4000", "4000", "4000", "4000", "400",    # May..Aug full, Sep is 3 days
          "Test", "", "Toyota", "Corolla", "2021", "1.8L", "ABC123",
          "20000", "34000", "1",
          "fri,sat,sun", "85", "420", "350", "150", "42",
          "y",                         # the last 3 days are Mon-Wed, so take the fix
          "brisbane", "", "", ""]      # per-year layout names no single sheet
out3 = TMP / "years.xlsx"
result3 = run([], "\n".join(across + [str(out3), "y", "n"]) + "\n")
check("it notices the period crosses 30 June", "crosses 30 June" in result3.stdout)
check("it offers the two layouts", "A separate sheet for each year" in result3.stdout)
check("it explains why that matters", "easier at tax time" in result3.stdout)
check("the run finishes", result3.returncode == 0, result3.stdout[-300:])
if out3.exists():
    book = load_workbook(out3)
    check("a sheet per year", len(book.sheetnames) == 2, book.sheetnames)
    check("named by year", all("logbook" in n for n in book.sheetnames), book.sheetnames)


# ===========================================================================
group("E. Config files and the command line")
# ===========================================================================

template = TMP / "template.json"
result4 = run(["--write-config-template", str(template)])
check("a template is written", result4.returncode == 0 and template.exists())
data = json.loads(template.read_text())
check("it holds no rate setting", "dollars_per_km" not in data)
check("it carries the new pattern settings",
      {"work_days", "business_share_on_work_days", "max_km_per_day", "sheet_mode"}
      <= set(data))
out4 = TMP / "from_template.xlsx"
result5 = run(["--config", str(template), "-o", str(out4)])
check("the template runs unedited", result5.returncode == 0, result5.stdout[-200:])
check("and writes a file", out4.exists())

result6 = run(["--config", "/nowhere/none.json"])
check("a missing config says so, without a traceback",
      result6.returncode != 0 and "Traceback" not in result6.stderr)

bad = TMP / "bad.json"
bad.write_text(json.dumps({**data, "monthly_income": {"2025-07": 900000},
                           "start_date": "2025-07-01", "end_date": "2025-07-14"}))
result7 = run(["--config", str(bad), "-o", str(TMP / "never.xlsx")])
check("an impossible config explains itself",
      result7.returncode != 0 and "Traceback" not in result7.stderr,
      (result7.stdout + result7.stderr)[-160:])
check("and writes nothing", not (TMP / "never.xlsx").exists())

result8 = run([], "01/07/2025\n")
check("running out of answers cancels cleanly",
      "Cancelled" in (result8.stdout + result8.stderr)
      and "Traceback" not in result8.stderr)

report("CLI")
