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


# ===========================================================================
group("B. The notebook file itself")
# ===========================================================================

import ast                                                     # noqa: E402
import json                                                    # noqa: E402
import re                                                      # noqa: E402
from harness import ROOT                                       # noqa: E402

NB = ROOT / "logbook.ipynb"
check("the notebook ships with the code", NB.exists())

book = json.loads(NB.read_text(encoding="utf-8"))
check("it is a version 4 notebook", book.get("nbformat") == 4)

cells = book["cells"]
markdown = ["".join(c["source"]) for c in cells if c["cell_type"] == "markdown"]
codes = ["".join(c["source"]) for c in cells if c["cell_type"] == "code"]
whole = "\n".join(markdown + codes)

check("every cell is markdown or code",
      all(c["cell_type"] in ("markdown", "code") for c in cells))

for i, body in enumerate(codes):
    try:
        ast.parse(body)
        ok = True
    except SyntaxError as exc:                                 # noqa: BLE001
        ok, exc_text = False, str(exc)
    check(f"code cell {i + 1} is valid Python", ok, "" if ok else exc_text)

# --- the repository address is fixed, not a box someone can edit -----------
setup = codes[0]
check("the setup cell names the repository", "REPO = " in setup)
check("but not as an editable box", "#@param" not in setup.split("REPO =")[1].split("\n")[0])
check("no placeholder address was left behind", "YOUR-NAME" not in whole)

# --- one pattern: a step heading, then its form ---------------------------
headings = [line for block in markdown for line in block.splitlines()
            if line.startswith("## ")]
numbered = [h for h in headings if "Step " in h]
check("six numbered steps, no more and no fewer", len(numbered) == 6, len(numbered))
for n in range(1, 7):
    check(f"step {n} has a heading of its own",
          any(f"Step {n} of 6" in h for h in numbered))
    check(f"step {n} has a form titled to match",
          any(f"#@title Step {n} of 6" in body for body in codes))

check("form titles stay plain text", all(
    line.isascii() for body in codes for line in body.splitlines()
    if line.startswith("#@title")))
check("every form cell hides its code",
      all('display-mode: "form"' in body.splitlines()[0]
          for body in codes if body.startswith("#@title")))

# --- every default is written out for the reader, in square brackets ------
def shown_as(value: str) -> str:
    text = value.strip()
    if text in ('""', "''"):
        return "[empty]"
    if text == "True":
        return "[ticked]"
    if text == "False":
        return "[unticked]"
    return "[" + text.strip("\"'") + "]"

PARAM = re.compile(r"^(\w+)\s*=\s*(.+?)\s+#@param", re.M)
params = []
for index, cell in enumerate(cells):
    if cell["cell_type"] != "code":
        continue
    body = "".join(cell["source"])
    before = "".join(cells[index - 1]["source"]) if index else ""
    for name, value in PARAM.findall(body):
        params.append((name, value, before))

check("the notebook has boxes to fill in", len(params) >= 14, len(params))
for name, value, before in params:
    check(f"{name} is explained in the step above it", f"**{name}**" in before)
    check(f"{name} shows its starting value as {shown_as(value)}",
          shown_as(value) in before, before[:0])

# --- nothing is used before the cell that sets it -------------------------
call = [body for body in codes if "make_logbook(" in body][0]
passed = set(re.findall(r"=\s*(\w+)[,)\n]", call.split("make_logbook(")[1]))
defined = {name for name, _v, _b in params}
check("the build cell only passes boxes the reader filled in",
      passed <= defined | {"sheet_per_financial_year", "seed"},
      sorted(passed - defined))

# --- directions a person can actually follow ------------------------------
for needle, why in [
        ("play button", "how to run a cell"),
        ("On a phone", "what to do on a phone"),
        ("folder icon", "where the file list is"),
        ("three dots", "how to download by hand"),
        ("If something goes wrong", "a troubleshooting section"),
        ("Runtime", "how to restart when stuck"),
        ("day/month/year", "the date format"),
        ("Have these ready", "what to collect first")]:
    check(f"it tells the reader {why}", needle in whole, needle)

check("it says the work stays on their own account",
      "your own account" in whole)

# --- none of the author's own details are used as examples ----------------
# The repository address is the one place the owner's name belongs: the notebook
# has to fetch the code from somewhere. Everywhere else it would be a stray
# personal detail in something strangers use, so the address is subtracted first
# and the rest of the text has to come back clean.
SLUG = "Mr-Yash-01/car-logbook"          # owner and repository, the fixed address
MINE = ("ya" + "sh", "vadu" + "kiya", "north lakes", "gab" + "loo", "@gmail")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
check("the notebook fetches the code from the fixed address",
      f"https://github.com/{SLUG}" in NB.read_text(encoding="utf-8"))
check("the Colab badge points at the same repository",
      f"colab.research.google.com/github/{SLUG}/blob/main/logbook.ipynb" in readme)
check("the Binder badge points at the same repository",
      f"mybinder.org/v2/gh/{SLUG}/main" in readme)

for folder in (ROOT, ROOT / "logbook", ROOT / "tests"):
    for path in sorted(folder.glob("*")):
        if path.suffix not in (".py", ".ipynb", ".md", ".txt") or not path.is_file():
            continue
        if path.name == Path(__file__).name:
            continue                       # this file names them in order to test
        lowered = path.read_text(encoding="utf-8", errors="ignore").lower()
        lowered = lowered.replace(SLUG.lower(), "")
        for word in MINE:
            check(f"{path.name} keeps personal details out ({word})",
                  word not in lowered)

# A spreadsheet shipped with the code is read by strangers too, so the samples
# get the same scan - the text inside a .xlsx is XML in a zip.
import zipfile                                                 # noqa: E402

ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
check("spreadsheets are kept out of the repository by default", "*.xlsx" in ignored)
samples = sorted(ROOT.glob("sample_*.xlsx"))
check("except the samples, which are let back in",
      all(f"!{path.name}" in ignored for path in samples),
      [path.name for path in samples])
check("two samples ship with the code", len(samples) == 2, len(samples))
for path in samples:
    inside = b""
    with zipfile.ZipFile(path) as book:
        for entry in book.namelist():
            if entry.endswith((".xml", ".rels")):
                inside += book.read(entry)
    lowered = inside.decode("utf-8", "ignore").lower()
    for word in MINE:
        check(f"{path.name} keeps personal details out ({word})",
              word not in lowered)


# --- the delivery wording, without a browser ------------------------------
from logbook.notebook import by_hand_lines, delivery_lines    # noqa: E402

by_hand = " ".join(by_hand_lines("Logbook_ABC123.xlsx"))
check("the by-hand steps name the file", "Logbook_ABC123.xlsx" in by_hand)
check("and are numbered", by_hand.strip().startswith("1."))
check("and name the folder icon", "folder icon" in by_hand)

off = " ".join(delivery_lines(Path("Logbook_ABC123.xlsx"), colab=False))
check("outside Colab it says where the file was left", "beside this notebook" in off)
check("and what opens it", "spreadsheet app" in off)


report("Notebook")
