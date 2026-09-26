#!/usr/bin/env python3
"""Run every suite. `python run_tests.py [-v]`"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITES = ["test_units.py", "test_pattern.py", "test_workbook.py",
          "test_notebook.py", "test_cli.py"]

total, failed = 0, []
for name in SUITES:
    result = subprocess.run([sys.executable, str(ROOT / "tests" / name)] + sys.argv[1:],
                            capture_output=True, text=True, cwd=ROOT)
    line = [x for x in result.stdout.splitlines() if "checks passed" in x
            or "FAILED" in x]
    print(f"{name:20} {line[0].strip() if line else 'no result'}")
    if result.returncode != 0:
        failed.append(name)
        print(result.stdout[-2000:])
    for word in (line[0].split() if line else []):
        if word.isdigit():
            total += int(word)
            break

print("\n" + "=" * 70)
if failed:
    print(f" FAILED: {', '.join(failed)}")
    sys.exit(1)
print(f" every suite passed - {total} checks")
print("=" * 70)
