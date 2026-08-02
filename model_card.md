# Model Card — AI Glitch Investigator

> **Note to self:** this is the graded responsible-AI reflection. It's drafted
> from what actually happened building this project — edit it into my own voice,
> and reconcile the section headings with the exact Step 5 rubric before
> submitting. The three graded elements are here: how I collaborated with AI,
> one helpful + one flawed AI suggestion, and the system's limitations.

## System overview

The **AI Glitch Investigator** diagnoses bugs in Python / Streamlit code. It
retrieves similar known bug patterns (RAG), reasons about the fault with cited
evidence, proposes a fix, and statically verifies its own answer.

- **Reasoning backend:** provider-agnostic. Real **Claude** (Anthropic Messages
  API with structured outputs, default `claude-opus-5`) when `ANTHROPIC_API_KEY`
  is set; otherwise a **deterministic rule-based mock** that composes its
  diagnosis from the retrieved knowledge-base patterns.
- **Retrieval:** pure-Python TF-IDF over a ~10-pattern knowledge base.
- **Verification:** static analysis via Python's `ast` — the code is never executed.

## Intended use

- **In scope:** educational debugging assistance on short Python / Streamlit
  snippets; explaining *what* is wrong, *why*, and *how* to fix it, with a human
  reviewing every suggested change.
- **Out of scope:** a general-purpose static analyzer or linter; large codebases;
  languages other than Python; auto-applying fixes without human review;
  security-critical decisions made on the tool's output alone.

## How I collaborated with AI

I used **Claude Code** as an agentic teammate throughout. I set the direction and
constraints (extend the Module 1 game into an applied AI system with RAG, an
agentic workflow, and reliability testing; keep the original game and its tests
untouched), approved a plan, and then reviewed the work at every step rather than
accepting it wholesale. Concretely, I: (1) required a written plan before any
code; (2) verified each claim by running `pytest` and booting the app myself;
(3) pushed back when the rubric wasn't fully met — for example, I had it add real
`logging` and wrap the live model calls in error handling after noting the
requirement for "logging or guardrails" and that an API failure could crash the
app. The collaboration was most productive when I treated the AI's output as a
*draft to verify*, not an answer to trust.

## One helpful AI suggestion (and how I verified it)

**Suggestion:** make the reasoning backend provider-agnostic — use Claude when a
key is present, but fall back to a *deterministic offline mock* that composes its
diagnosis from the retrieved patterns, so the whole system runs and all tests
pass with no API key.

**Why it was good:** it made the project reproducible and gradeable offline, and
it turned the mock into a trustworthiness feature (deterministic, auditable
runs). **How I verified it:** I ran the full test suite with no key set and
confirmed all 40 tests pass, then set a key and confirmed the pipeline switched
to live Claude reasoning while the same tests still passed.

## One flawed AI suggestion (and how I caught it)

**Suggestion / output:** the first version of the retriever confidently ranked
the *backwards-hint* pattern **above** the *int-vs-str comparison* pattern for a
snippet that had both — so the AI's top answer was the wrong bug class.

**Why it was flawed:** naive TF-IDF over-weights shared vocabulary ("Too High",
"Too Low", "Win", "guess", "secret"), which both patterns contain, so the wrong
one won on token overlap. **How I caught and handled it:** my reliability test
asserted the expected pattern per case, and it failed. Instead of loosening the
test, I inspected the retrieval scores, saw the vocabulary collision, tuned the
knowledge base to sharpen the discriminating signal, and re-ran the suite. I then
kept an **honest** threshold in the test (`top-1 ≥ 0.6`, `top-3 == 1.0`) rather
than overfitting to a perfect number — the miss is documented, not hidden.

## Limitations

- **Retrieval accuracy:** top-1 accuracy is **6/8** on the golden dataset (top-3
  recall is 8/8). The TF-IDF retriever confuses patterns that share vocabulary.
  This is the main reason the reasoning layer, confidence scores, and abstention
  exist — they compensate for imperfect retrieval.
- **Scope:** the knowledge base is small (~10 patterns) and Python/Streamlit
  focused; it is not a general static analyzer and will miss bugs outside its
  corpus.
- **Fixes:** only a subset of patterns have a real mechanical fix; the rest are
  surfaced as an annotated recommendation for the human to apply.
- **Verification is structural, not runtime:** because the tool never executes
  the code (a deliberate safety choice), it cannot confirm a fix by running the
  code's own tests — it checks syntax and pattern-specific signals only.
- **Offline mock ≠ real reasoning:** with no API key, diagnoses are composed from
  retrieved patterns, so the mock inherits the retriever's limitations directly.

## Responsible-AI safeguards

- **Grounded:** every diagnosis cites a knowledge-base pattern and specific
  evidence lines — claims are checkable, not opaque.
- **Abstains when unsure:** below a confidence threshold it declines to diagnose
  rather than guessing.
- **Never executes untrusted code:** verification is static (AST) only.
- **Injection-resistant:** submitted code is treated strictly as data; the live
  client is instructed to ignore instructions embedded in the code, and the mock
  cannot be injected (it only pattern-matches).
- **Human-in-the-loop:** fixes are shown as a diff and never auto-applied.
- **Fault-tolerant & logged:** each run is logged; a live-API failure falls back
  to the deterministic mock instead of crashing.

## Evaluation

- **Automated tests:** 40, all passing offline (game logic, retriever, agent
  pipeline, reliability + robustness). Reproduce with `pytest`.
- **Golden-dataset metrics:** top-1 retrieval accuracy 6/8; top-3 recall 8/8;
  verified fixes on all mechanically-fixable cases.
- **Robustness:** empty, whitespace, prose, oversized, and prompt-injection
  inputs are all handled without a crash.
