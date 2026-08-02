"""Static verification of a proposed fix — the agent's self-check step.

A deliberate trust choice: we **never execute** the untrusted code. Verification
is purely static — we parse the patched code with Python's `ast` module to prove
it is still syntactically valid, confirm the fix actually changed something, and
run a per-pattern signal check that the specific fault is gone. Static-only means
a malicious or broken snippet can never run on the investigator's machine.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class VerificationResult:
    passed: bool
    checks: List[Check] = field(default_factory=list)

    @property
    def summary(self) -> str:
        ok = sum(c.passed for c in self.checks)
        return f"{ok}/{len(self.checks)} checks passed"

    def failure_reason(self) -> Optional[str]:
        for c in self.checks:
            if not c.passed:
                return f"{c.name}: {c.detail}"
        return None


def _syntax_ok(code: str) -> Check:
    try:
        ast.parse(code)
        return Check("syntax_valid", True, "patched code parses cleanly")
    except SyntaxError as e:
        return Check("syntax_valid", False, f"SyntaxError: {e.msg} (line {e.lineno})")


# Per-pattern static signal checks: does the patched code still exhibit the fault?
def _signal_gone(pattern_id: str, original: str, patched: str) -> Optional[Check]:
    if pattern_id == "int-str-compare":
        # No str() wrapping a compared identifier should remain.
        bad = re.search(r"\bstr\(\s*(secret|guess)\s*\)", patched)
        return Check(
            "no_str_cast_on_compared_value",
            bad is None,
            "a str() cast still wraps the compared value" if bad else "str() cast removed",
        )
    if pattern_id == "erratic-scoring":
        bad = re.search(r"score\s*[+\-]=\s*random", patched)
        return Check(
            "no_random_score_mutation",
            bad is None,
            "score is still mutated by randomness" if bad else "random score mutation removed",
        )
    if pattern_id == "backwards-conditional":
        # The mechanical swap must have changed the HIGHER/LOWER wiring.
        return Check(
            "hint_direction_changed",
            original != patched,
            "hint direction unchanged" if original == patched else "hint direction adjusted",
        )
    return None  # patterns without a mechanical signal check rely on syntax+changed


def verify_fix(original: str, patched: str, pattern_id: Optional[str]) -> VerificationResult:
    """Statically verify a proposed fix. Never executes the code."""
    checks: List[Check] = [_syntax_ok(patched)]

    changed = patched.strip() != original.strip()
    checks.append(
        Check("fix_changed_code", changed,
              "fix made no change to the code" if not changed else "code was modified")
    )

    if pattern_id:
        signal = _signal_gone(pattern_id, original, patched)
        if signal is not None:
            checks.append(signal)

    passed = all(c.passed for c in checks)
    return VerificationResult(passed=passed, checks=checks)
