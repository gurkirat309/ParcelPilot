"""Rule 3 enforcement: the wall clock is banned in source.

Greps the source tree for `datetime.now(`, `date.today(`, and `time.time(`.
`src/config.py` defines the sanctioned `now()` wrapper around the frozen
snapshot and is the only allowed reference to the concept.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED = [re.compile(p) for p in (r"datetime\.now\(", r"date\.today\(", r"time\.time\(")]
SCAN_DIRS = ["src", "scripts", "evals"]

# Strip string/backtick spans so prose that NAMES the banned calls (docstrings,
# rule text) is not flagged — only genuine code calls are.
_STRIP = re.compile(r"`[^`]*`|'[^']*'|\"[^\"]*\"")


def _strip_literals(line: str) -> str:
    return _STRIP.sub("", line)


def test_no_wall_clock_calls():
    offenders: list[str] = []
    for d in SCAN_DIRS:
        for path in (ROOT / d).rglob("*.py"):
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                code = _strip_literals(line)
                if "#" in code:
                    code = code[: code.index("#")]
                if any(pat.search(code) for pat in BANNED):
                    offenders.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")
    assert not offenders, "Wall-clock usage found (Rule 3):\n" + "\n".join(offenders)
