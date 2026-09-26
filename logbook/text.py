"""Reading and cleaning what people type, and the format rules each field follows.

Every front end - command line, bot, web - runs these same checks, so a bad value
is caught the same way and explained the same way wherever it came from.
"""

from __future__ import annotations

import re
from datetime import date

from .errors import fail

EXCEL_TEXT_LIMIT = 500
BIDI_MARKS = dict.fromkeys(range(0x202A, 0x202F))   # text-direction overrides
INVALID_SHEET_CHARS = set(r"[]:*?/\\")

# Australian plates run to 6 characters in most states, 7 for personalised ones.
REGO_MAX = 7
REGO_OK = re.compile(r"^[A-Z0-9]{1,%d}$" % REGO_MAX)
NAME_OK = re.compile(r"^[^\W_][\w .,'&/()+-]{0,39}$", re.UNICODE)
ENGINE_OK = re.compile(r"^[\w. ()/-]{1,20}$", re.UNICODE)
PERSON_OK = re.compile(r"^[^\W\d_][\w .,'-]{0,59}$", re.UNICODE)

ODOMETER_MAX = 2_000_000          # further than any car goes
INCOME_MONTH_MAX = 1_000_000      # one month's earnings, generously
MAX_WORDINGS = 40                 # entries kept from one list of reasons or areas
MAX_WORDING_LENGTH = 120


def sanitize_text(value, limit: int = EXCEL_TEXT_LIMIT) -> str:
    """Strip control characters and direction tricks, flatten newlines, cap length."""
    if value is None:
        return ""
    text = str(value).translate(BIDI_MARKS)
    text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\t\n")
    text = text.replace("\t", " ").replace("\n", " ").strip()
    while "  " in text:
        text = text.replace("  ", " ")
    return text[:limit]


def sanitize_sheet_name(name) -> str:
    """Excel bans [ ] : * ? / \\ in sheet names and caps them at 31 characters."""
    clean = sanitize_text(name, 40)
    clean = "".join("-" if ch in INVALID_SHEET_CHARS else ch for ch in clean)
    clean = clean.strip("'").strip()
    return clean[:31] or "Logbook"


# --- numbers ---------------------------------------------------------------

def parse_numbers(text) -> list:
    """Pull every number out of a typed line, thousands separators and all.

    "45,230 to 55,230" and "45230, 55230" both give [45230.0, 55230.0]: a comma
    disappears only between a digit and exactly three more, so it reads as a
    thousands separator rather than a divider between two numbers.
    """
    cleaned = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", str(text or ""))
    cleaned = cleaned.replace("$", " ")
    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", cleaned)]


def parse_amount(raw, label: str, *, minimum=None, maximum=None, default=None) -> float:
    """Read one number a person typed - dollar signs, commas and per-cent signs and all."""
    text = str(raw or "").strip().replace(",", "").replace("$", "").replace("%", "")
    if not text:
        if default is not None:
            return default
        fail(f"{label} is needed.")
    try:
        value = float(text)
    except ValueError:
        fail(f"{label} needs to be a number.")
    if minimum is not None and value < minimum:
        fail(f"{label} cannot be below {minimum:g}.")
    if maximum is not None and value > maximum:
        fail(f"{label} cannot be above {maximum:g}.")
    return value


def parse_share(raw, label: str, *, default=None) -> float:
    """Read a share written either way: 80, 80%, or 0.8 all mean the same thing."""
    text = str(raw or "").strip()
    if not text:
        if default is not None:
            return default
        fail(f"{label} is needed.")
    value = parse_amount(text, label, minimum=0, maximum=100)
    if value > 1 or "%" in text:
        value = value / 100
    return value


# --- fields ----------------------------------------------------------------

def clean_registration(raw, required: bool = True) -> str:
    """Australian plate: up to seven letters and numbers; spaces and dashes ignored."""
    text = sanitize_text(raw, 60).upper().replace(" ", "").replace("-", "")
    if not text:
        if required:
            fail("A registration number is needed.")
        return ""
    if not REGO_OK.match(text):
        fail(f'"{text}" is not an Australian registration. Plates are up to '
             f"{REGO_MAX} letters and numbers, with no symbols.")
    return text


def clean_vehicle_word(raw, label: str, required: bool = True) -> str:
    """Make or model: something that reads like a name, not a paragraph."""
    text = sanitize_text(raw, 200)
    if len(text) > 40:
        fail(f"That {label} is {len(text)} characters long. Keep it under 40.")
    if not text:
        if required:
            fail(f"The {label} is needed.")
        return ""
    if not NAME_OK.match(text):
        fail(f"That {label} has characters that do not belong in one. Letters, "
             f"numbers, spaces and - . , / & are fine, up to 40 characters.")
    return text


def clean_engine(raw, required: bool = True) -> str:
    """Engine capacity such as 1.8L, 1798cc, V8, 2.0 (turbo)."""
    text = sanitize_text(raw, 200)
    if len(text) > 20:
        fail("Write the engine capacity briefly, like 1.8L or 1798cc.")
    if not text:
        if required:
            fail("The engine capacity is needed.")
        return ""
    if not ENGINE_OK.match(text) or not any(ch.isdigit() for ch in text):
        fail("Write the engine capacity like 1.8L or 1798cc - it needs a number in it.")
    return text


def clean_person(raw, label: str = "name") -> str:
    text = sanitize_text(raw, 200)
    if len(text) > 60:
        fail(f"That {label} is {len(text)} characters long. Keep it under 60.")
    if not text:
        return ""
    if not PERSON_OK.match(text):
        fail(f"That {label} has characters that do not belong in one.")
    return text


def clean_abn(raw) -> str:
    """An ABN is eleven digits and carries its own check."""
    text = "".join(ch for ch in sanitize_text(raw, 30) if not ch.isspace())
    if not text:
        return ""
    digits = text.replace("-", "")
    if not digits.isdigit() or len(digits) != 11:
        fail("An ABN is 11 digits.")
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    numbers = [int(d) for d in digits]
    numbers[0] -= 1
    if sum(w * n for w, n in zip(weights, numbers)) % 89 != 0:
        fail("That ABN does not check out - one of the digits is wrong.")
    return f"{digits[:2]} {digits[2:5]} {digits[5:8]} {digits[8:]}"


def clean_odometer(value, label: str) -> int:
    return int(parse_amount(value, label, minimum=0, maximum=ODOMETER_MAX))


def clean_year(raw) -> str:
    text = sanitize_text(raw, 4)
    if not text:
        return ""
    if not text.isdigit() or not 1900 <= int(text) <= date.today().year + 1:
        fail(f"A year of manufacture should be between 1900 and {date.today().year + 1}.")
    return text


def clean_wordings(raw, fallback=()) -> list:
    """A list of reasons or areas: trimmed, de-duplicated, capped, never empty if a fallback is given."""
    items = [raw] if isinstance(raw, str) else list(raw or [])
    cleaned, seen = [], set()
    for item in items[:MAX_WORDINGS]:
        value = sanitize_text(item, MAX_WORDING_LENGTH)
        if value and value.lower() not in seen:
            seen.add(value.lower())
            cleaned.append(value)
    return cleaned or list(fallback)
