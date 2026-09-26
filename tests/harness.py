"""A small shared harness, so every suite reports the same way."""

from __future__ import annotations

import builtins
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASSED: list = []
FAILED: list = []
_group = ""
VERBOSE = "-v" in sys.argv


def group(name: str):
    global _group
    _group = name
    print(f"\n{name}\n" + "-" * len(name))


def check(label: str, condition, detail=""):
    if condition:
        PASSED.append(label)
        if VERBOSE:
            print(f"  pass  {label}")
    else:
        FAILED.append(f"{_group} :: {label} {detail}")
        print(f"  FAIL  {label} {detail}")


def refuses(fn, *args, **kwargs):
    """Run fn; return (refused?, message)."""
    from logbook.errors import LogbookError
    try:
        with redirect_stdout(io.StringIO()):
            fn(*args, **kwargs)
        return False, ""
    except LogbookError as exc:
        return True, str(exc)
    except SystemExit as exc:
        return True, str(exc)


def feed(answers):
    it = iter(answers)

    def fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError
    return fake_input


def with_input(answers, fn, *args, **kwargs):
    real = builtins.input
    builtins.input = feed(answers)
    try:
        with redirect_stdout(io.StringIO()):
            return fn(*args, **kwargs)
    finally:
        builtins.input = real


def report(title: str):
    print("\n" + "=" * 70)
    if FAILED:
        print(f" {title}: {len(PASSED)} passed, {len(FAILED)} FAILED")
        for line in FAILED:
            print(f"   - {line}")
        sys.exit(1)
    print(f" {title}: all {len(PASSED)} checks passed")
    print("=" * 70)
