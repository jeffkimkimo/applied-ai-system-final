"""The agentic pipeline (Module 5): retrieve → diagnose → fix → verify → refine.

`investigate(code)` runs a bounded, multi-step agent loop and returns a full,
inspectable trace of every step — the retrieval scores, the reasoned diagnosis
with cited evidence, each fix attempt, and its verification result. Nothing is
hidden: the trace is what the UI renders and what the reliability tests assert
against.

Design guardrails baked in here:
  * Input is validated first (empty / too-large / clearly-not-code) so the agent
    degrades gracefully instead of hallucinating on junk.
  * The refine loop is bounded (MAX_REFINEMENTS) so it always terminates.
  * The submitted code is only ever passed as data to the retriever and client;
    it is never executed and never treated as instructions.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .knowledge_base import KnowledgeBase, RetrievedPattern
from .llm import Diagnosis, FixProposal, MockClient, get_client
from .verify import VerificationResult, verify_fix

MAX_REFINEMENTS = 2          # bounded self-correction loop
MAX_CODE_CHARS = 20_000      # oversized-input guardrail
TOP_K = 3                    # how many patterns the RAG layer surfaces

# Every run logs what it does through this named logger. It is silent by default
# (no handler) so importing the library never spams output; the Streamlit app
# and `logging.basicConfig(...)` both attach a handler to surface it.
logger = logging.getLogger("glitch_investigator")


@dataclass
class Step:
    """One entry in the agent's trace, for display and auditing."""

    name: str
    detail: str


@dataclass
class InvestigationResult:
    ok: bool
    message: str = ""
    backend: str = ""
    retrieved: List[RetrievedPattern] = field(default_factory=list)
    diagnosis: Optional[Diagnosis] = None
    fix: Optional[FixProposal] = None
    verification: Optional[VerificationResult] = None
    refinements: int = 0
    trace: List[Step] = field(default_factory=list)

    @property
    def diff(self) -> str:
        """Unified diff between the original and patched code (empty if no fix)."""
        if not self.fix or not self.fix.changed or self._original is None:
            return ""
        return "".join(
            difflib.unified_diff(
                self._original.splitlines(keepends=True),
                self.fix.patched_code.splitlines(keepends=True),
                fromfile="original.py",
                tofile="fixed.py",
            )
        )

    _original: Optional[str] = None


def _validate(code: str) -> Optional[str]:
    """Return an error message if the input isn't worth investigating, else None."""
    if code is None or not code.strip():
        return "No code submitted — paste some Python to investigate."
    if len(code) > MAX_CODE_CHARS:
        return f"Input too large ({len(code)} chars). Limit is {MAX_CODE_CHARS}."
    # Cheap "is this code at all?" heuristic: real Python snippets contain some
    # structural tokens. Prose / prompt-injection text usually does not.
    structural = ("=", "(", ":", "def ", "import ", "if ", "st.", "return")
    if not any(tok in code for tok in structural):
        return "This doesn't look like Python code — nothing to investigate."
    return None


def investigate(code: str, kb: Optional[KnowledgeBase] = None, client=None) -> InvestigationResult:
    """Run the full agentic investigation and return an inspectable trace."""
    kb = kb or KnowledgeBase.load()
    client = client or get_client()

    logger.info("investigate: %d chars, backend=%s", len(code or ""), client.name)

    err = _validate(code)
    if err:
        logger.info("investigate: input rejected — %s", err)
        return InvestigationResult(ok=False, message=err, backend=client.name)

    result = InvestigationResult(ok=True, backend=client.name)
    result._original = code

    # 1. Retrieve (RAG).
    retrieved = kb.retrieve(code, k=TOP_K)
    result.retrieved = retrieved
    logger.info("retrieve: %s", [(r.pattern.id, r.score) for r in retrieved] or "none")
    result.trace.append(Step(
        "retrieve",
        "Top patterns: " + (", ".join(f"{r.pattern.id}({r.score})" for r in retrieved) or "none"),
    ))

    # 2. Diagnose (reasoning, grounded in the retrieved patterns).
    # A live model call can fail (network, rate limit, malformed response). If it
    # does, we log it and fall back to the deterministic offline mock so the user
    # still gets an answer instead of a crash.
    try:
        diagnosis = client.diagnose(code, retrieved)
    except Exception as exc:  # noqa: BLE001 — deliberate safety net around the LLM
        logger.warning("diagnose failed on %s (%s); falling back to offline mock", client.name, exc)
        client = MockClient()
        result.backend = f"{client.name} (fallback after live error)"
        result.trace.append(Step("fallback", f"Live backend errored ({exc}); using offline mock."))
        diagnosis = client.diagnose(code, retrieved)
    result.diagnosis = diagnosis
    logger.info(
        "diagnose: %s (conf=%s, abstained=%s, lines=%s)",
        diagnosis.bug_name, diagnosis.confidence, diagnosis.abstained, diagnosis.evidence_lines,
    )
    if diagnosis.abstained:
        logger.info("investigate: abstained (no confident match)")
        result.trace.append(Step("diagnose", "Abstained — no confident match; not guessing."))
        result.message = "No confident diagnosis. The Investigator abstains rather than guess."
        return result
    result.trace.append(Step(
        "diagnose",
        f"{diagnosis.bug_name} (confidence {diagnosis.confidence}), "
        f"evidence lines {diagnosis.evidence_lines}",
    ))

    # 3–4. Propose a fix, verify it, and refine on failure (bounded loop).
    feedback: Optional[str] = None
    fix: Optional[FixProposal] = None
    verification: Optional[VerificationResult] = None
    for attempt in range(MAX_REFINEMENTS + 1):
        try:
            fix = client.propose_fix(code, diagnosis, retrieved, feedback=feedback)
        except Exception as exc:  # noqa: BLE001 — same safety net for the fix call
            logger.warning("propose_fix failed on %s (%s); using offline mock", client.name, exc)
            client = MockClient()
            fix = client.propose_fix(code, diagnosis, retrieved, feedback=feedback)
        verification = verify_fix(code, fix.patched_code, diagnosis.pattern_id)
        logger.info(
            "fix+verify attempt %d: changed=%s, %s",
            attempt + 1, fix.changed, verification.summary,
        )
        result.trace.append(Step(
            f"fix+verify (attempt {attempt + 1})",
            f"{fix.summary} → {verification.summary}",
        ))
        if verification.passed:
            break
        feedback = verification.failure_reason()
        result.refinements = attempt + 1

    result.fix = fix
    result.verification = verification
    if verification and verification.passed:
        result.message = f"Diagnosed and verified a fix for: {diagnosis.bug_name}."
    else:
        result.message = (
            f"Diagnosed {diagnosis.bug_name}, but the proposed fix did not pass "
            f"verification after {MAX_REFINEMENTS} refinements — review manually."
        )
    logger.info("investigate: done — %s", result.message)
    return result
