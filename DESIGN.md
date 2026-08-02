# Design — AI Glitch Investigator

> How the AI works, and why you can trust it.

## The problem it solves

In Module 1 you hand-debugged a glitchy Streamlit guessing game: you found the
state bug, the backwards hints, and the int-vs-str comparison, then fixed and
tested them. The **AI Glitch Investigator** is the system that does that
investigation *for* you: paste buggy Python/Streamlit code and it retrieves
similar known bug patterns, reasons about the fault with cited evidence,
proposes a fix, and verifies its own answer — surfacing every step so a human
stays in control.

The debugged game is the flagship demo case: the "Original glitchy game" preset
is the pre-fix code, and the Investigator rediscovers its bugs.

## How it works — the pipeline

```
   paste code
       │
       ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 1. RETRIEVE  │──▶│ 2. DIAGNOSE  │──▶│ 3. PROPOSE   │──▶│ 4. VERIFY    │
│ (RAG / M4)   │   │ (reason /M3) │   │    FIX (M5)  │   │ static (M5)  │
│ TF-IDF over  │   │ grounded in  │   │ patch + diff │   │ AST, no exec │
│ bug patterns │   │ patterns +   │   │              │   │              │
│ + scores     │   │ cited lines  │   │              │   │  fail?       │
└──────────────┘   └──────────────┘   └──────────────┘   └──────┬───────┘
                                            ▲                    │ refine
                                            └────────────────────┘ (bounded ≤2)
```

Each module's concept maps to one stage:

| Module | Concept | Where it lives |
|---|---|---|
| M1–2 | debugging & design | the game (`app.py`, `logic_utils.py`) + this system's module design |
| M3 | reasoning | `llm.py` — structured, evidence-cited diagnosis |
| M4 | retrieval / RAG | `knowledge_base.py` — TF-IDF retriever over `data/bug_patterns.json` |
| M5 | agentic workflow | `agent.py` — retrieve → diagnose → fix → verify → refine |
| M5 | reliability testing | `cases/cases.json` + `tests/test_reliability.py` |

### 1. Retrieve (RAG)
A local knowledge base of ~10 common Python/Streamlit bug patterns
(`data/bug_patterns.json`). Each pattern is a document (name, symptom, cause,
fix, signals). The retriever (`knowledge_base.py`) scores every pattern against
the pasted code using **TF-IDF cosine similarity**, implemented in pure Python —
no embeddings API, no heavy dependencies, so it runs and is graded fully
offline. Every result carries a numeric score and the tokens that matched, so
retrieval is transparent.

### 2. Diagnose (reasoning)
The code plus the retrieved patterns go to the reasoning layer, which returns a
**structured diagnosis**: which pattern, why, the specific evidence lines, and a
confidence score. When no pattern matches with enough confidence, it **abstains**
instead of guessing.

### 3. Propose fix
A patched version of the code plus a unified diff. Nothing is auto-applied — the
diff is shown for human review.

### 4. Verify + refine
The proposed fix is checked **statically** (`verify.py`): the patch must still
parse (AST), must actually change the code, and must clear a pattern-specific
signal check (e.g. "no `str()` cast remains on the compared value"). If
verification fails, the agent refines — a **bounded** loop (≤ 2 retries) so it
always terminates.

## The provider-agnostic backend

`get_client()` returns a real **Claude** client (`AnthropicClient`, Anthropic
Messages API with structured outputs) when `ANTHROPIC_API_KEY` — or an
`ant auth login` profile — is available, and a deterministic **`MockClient`**
otherwise. Both expose the same `diagnose` / `propose_fix` interface, so the
pipeline is identical either way. The mock composes its diagnosis purely from the
retrieved patterns, which is why the whole system runs and every test passes with
no key.

## Why it's trustworthy

Responsible design was a first-class constraint, not an afterthought:

1. **Grounded, not hallucinated.** Every diagnosis cites a knowledge-base
   pattern and specific evidence lines. You can check the claim against the code.
2. **Knows what it doesn't know.** Below a confidence threshold the system
   abstains ("no confident match") rather than inventing a bug.
3. **Never executes your code.** Verification is static AST analysis only. A
   malicious or broken snippet can never run on the investigator's machine.
4. **Injection-resistant.** The pasted code is always treated as *data*. The mock
   can't be prompt-injected (it only pattern-matches); the live client is
   instructed to ignore any instructions embedded in the code.
5. **Human-in-the-loop.** Fixes are shown as a diff and never auto-applied.
6. **Reproducible & auditable.** The offline mock is deterministic, the full
   agent trace is exposed in the UI, and reliability is measured on a labeled
   golden dataset.
7. **Logged & fault-tolerant.** Every run logs what it does (retrieval,
   diagnosis, each fix/verify attempt, final outcome) through a
   `glitch_investigator` logger. If a live model call fails mid-run (network,
   rate limit, malformed response), the pipeline logs it and **falls back to the
   deterministic mock** rather than crashing — the app never dies on an API hiccup.

## Honest limitations

- The TF-IDF retriever gets **top-1 accuracy of 6/8 and top-3 recall of 8/8** on
  the golden set. It confuses patterns that share vocabulary (e.g. an
  int-vs-str comparison that also prints "Too High"/"Too Low"). This is *why*
  the reasoning layer, confidence scores, and abstention matter — and why the
  reliability test asserts an honest threshold, not a suspicious 100%.
- The knowledge base is small and Python/Streamlit-focused; it is not a general
  static analyzer.
- Mechanical fixes exist only for a subset of patterns; others are surfaced as
  an annotated recommendation for the human to apply.

## Reliability testing

`tests/test_reliability.py` runs the Investigator over the labeled snippets in
`cases/cases.json` (several are the game's real bugs) and asserts: perfect top-3
retrieval recall, top-1 accuracy above threshold, no crash on any case, verified
fixes on mechanically-fixable cases, and clean handling of robustness inputs
(empty, whitespace, prose, oversized, prompt-injection). All deterministic,
all offline.
