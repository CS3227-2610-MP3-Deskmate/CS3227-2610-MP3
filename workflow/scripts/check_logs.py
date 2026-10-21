"""Check every session log against workflow/skills/log.md (issue #36).

Reports, for each log: a missing title, a missing `Slice:` or `Cost:` header
line, a missing required section, a file name that is not `NNN-kebab.md`, and a
number that repeats within one author's folder. Exits non-zero on any finding.

Run from the repository root: `python3 workflow/scripts/check_logs.py`.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "logs"
SECTIONS = (
    "## Requests",
    "## Agent runs",
    "## Decisions and corrections",
    "## Problems",
)
NAME = re.compile(r"^(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")


def findings(path):
    """Return this log file's problems as (path, message) pairs."""
    problems = []
    name = NAME.match(path.name)
    if not name:
        problems.append((path, "file name is not NNN-kebab.md"))
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        problems.append((path, "first line is not a title"))
    for field in ("Slice:", "Cost:"):
        if not any(line.startswith(field) for line in lines[:6]):
            problems.append((path, f"header has no {field} line"))
    for section in SECTIONS:
        if section not in text:
            problems.append((path, f"missing section {section}"))
    return problems


def main():
    """Check every author's folder and report duplicates and gaps."""
    problems = []
    for folder in sorted(p for p in LOGS.iterdir() if p.is_dir()):
        numbers = {}
        for path in sorted(folder.glob("*.md")):
            problems.extend(findings(path))
            match = NAME.match(path.name)
            if match:
                numbers.setdefault(int(match.group(1)), []).append(path.name)
        for number, names in sorted(numbers.items()):
            if len(names) > 1:
                problems.append(
                    (folder, f"number {number:03d} used by {', '.join(names)}")
                )
        expected = list(range(1, len(numbers) + 1))
        gaps = sorted(set(expected) - set(numbers))
        if gaps:
            problems.append((folder, f"no log for number(s) {gaps}"))
    for path, message in problems:
        print(f"{path.relative_to(ROOT)}: {message}")
    print(f"{len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
