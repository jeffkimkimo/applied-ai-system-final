# Model Card — AI Glitch Investigator

> **Note to self:** this is the graded responsible-AI reflection. It's drafted
> from what actually happened building this project — edit it into my own voice
> before submitting. The four required questions each have their own labeled
> header below.

## System overview

The **AI Glitch Investigator** diagnoses bugs in Python / Streamlit code. It
retrieves similar known bug patterns (RAG), reasons about the fault with cited
evidence and a confidence score, proposes a fix, and statically verifies its own
answer — keeping a human in the loop.

- **Reasoning backend:** provider-agnostic. Real **Claude** (Anthropic Messages
  API with structured outputs, default `claude-opus-5`) when `ANTHROPIC_API_KEY`
  is set; otherwise a **deterministic rule-based mock** that composes its
  diagnosis from the retrieved knowledge-base patterns.
- **Retrieval:** pure-Python TF-IDF over a ~10-pattern knowledge base.
- **Verification:** static analysis via Python's `ast` — the code is never executed.

## Intended use

- **In scope:** educational debugging help on short Python / Streamlit snippets —
  explaining *what* is wrong, *why*, and *how* to fix it, with a human reviewing
  every suggested change.
- **Out of scope:** a general static analyzer or linter; large codebases;
  non-Python languages; auto-applying fixes; deciding whether code is *secure*.

---

## 1. What are the limitations or biases in your system?

**Limitations**

- **Retrieval accuracy:** top-1 accuracy is **6/8** on the golden dataset (top-3
  recall is 8/8). The retriever confuses patterns that share vocabulary.
- **Small, narrow corpus:** ~10 patterns, Python/Streamlit-focused — it will miss
  any bug it has no pattern for. It is a pattern-matcher, not a general analyzer.
- **Structural (not runtime) verification:** because it never executes the code
  (a deliberate safety choice), it can't confirm a fix by running the code's
  tests — it checks syntax and pattern-specific signals only.
- **Mechanical fixes for a subset only:** other patterns get an annotated
  recommendation for the human to apply, not an automatic patch.

**Biases**

- **Corpus / selection bias:** the system can only "see" the bug classes I chose
  to include, and those are skewed toward the original game's bugs. My blind
  spots become the system's blind spots — a bug I didn't think to add simply
  doesn't exist to it.
- **Lexical (vocabulary) bias:** TF-IDF ranks by token overlap, so a pattern with
  more or more-common keywords, or one that happens to share words with the
  submitted code, gets an unfair boost. This directly caused the two mis-rankings
  in testing (int-vs-str lost to "backwards hint" because both mention "Too
  High/Too Low").
- **Confidence miscalibration:** in the offline backend, confidence is derived
  from the retrieval score, not from correctness — so the system is biased toward
  *overconfidence* and can report a wrong answer at ~0.88 confidence.
- **Language/framework bias:** English-language patterns and Python/Streamlit
  idioms; it would under-serve other languages or coding styles.

---

## 2. Could your AI be misused, and how would you prevent that?

**Misuse 1 — leaking sensitive code.** With a live key, submitted code is sent to
a third-party API. *Prevention:* the **offline deterministic mock is the default**
(nothing leaves the machine without an explicit key), the app **discloses** which
backend is active in the sidebar, and the logs record only step metadata — **never
the submitted code**.

**Misuse 2 — over-trust / automation bias.** A user could treat a confident
diagnosis as ground truth and apply a wrong fix. *Prevention:* the human stays in
the loop — fixes are shown as a **diff and never auto-applied**, the system
**abstains** when unsure, and it always shows its **evidence and confidence** so
the user can judge rather than defer.

**Misuse 3 — mistaking it for a security scanner.** Someone might ask "is this
code safe?" *Prevention:* it is scoped and documented as a *bug-pattern* tool, not
a security analyzer; it **never executes code**, so it makes no runtime safety
claims, and "deciding whether code is secure" is explicitly out of scope.

**Misuse 4 — prompt injection.** Malicious text inside the code could try to
hijack the AI's output. *Prevention:* the code is always treated as **data, not
instructions** — the live client is told to ignore embedded instructions, and the
mock only pattern-matches, so it can't be injected (tested by
`test_prompt_injection_is_treated_as_data`).

---

## 3. What surprised you while testing your AI's reliability?

**Confidence and correctness were decoupled.** The biggest surprise: the two
cases the retriever got *wrong* were still reported at ~0.88 confidence. I had
assumed a high-confidence answer was a reliable one, and testing proved that
false — "confident" and "correct" are different axes. That single finding
reshaped the whole trust model of the project and is why abstention and mandatory
human review exist.

**The information was always there — ranking was the problem.** Top-3 recall was a
perfect 8/8 even though top-1 was 6/8. So the failure wasn't that retrieval
*missed* the right pattern; it *found* it and mis-ranked it. That reframed how I'd
improve the system — better ranking (embeddings), not a bigger corpus.

**The bug was invisible by eye.** In the app the wrong diagnosis looked perfectly
plausible; only a failing automated test exposed it. That drove home that
plausible-looking AI output is exactly the output you can't trust without a test.

---

## 4. Collaborating with AI during this project

I used **Claude Code** as an agentic teammate: I set the direction and
constraints, approved a plan before any code was written, and then **verified
every claim** by running `pytest` and booting the app myself rather than trusting
the output. The collaboration worked best when I treated the AI's work as a
*draft to verify*, not an answer to accept.

### One helpful AI suggestion (and how I verified it)

The AI proposed making the backend **provider-agnostic with a deterministic
offline mock** — use Claude when a key is present, otherwise fall back to a mock
that composes its diagnosis from the retrieved patterns. This made the project
run and pass all tests **with no API key**, and turned reproducibility itself into
a trust feature. I verified it by running the full suite with no key (40/40 pass),
then with a key (pipeline switches to live Claude, tests still pass).

### One flawed AI suggestion (and how I caught it)

The first retriever the AI built **confidently ranked the wrong bug first** for a
snippet that had both an int-vs-str comparison and hint text — it put "backwards
hint" above "int-vs-str comparison." It was flawed because naive TF-IDF
over-weights shared vocabulary. I caught it because a reliability test asserted
the expected pattern per case and **failed**. Instead of loosening the test to
hide the miss, I inspected the scores, tuned the knowledge base, and re-ran —
improving top-1 accuracy from 5/8 to 6/8 while keeping an **honest** threshold.

---

## Responsible-AI safeguards (summary)

Grounded (cited evidence), abstains when unsure, never executes untrusted code,
injection-resistant (code treated as data), human-in-the-loop (diff, never
auto-applied), and logged + fault-tolerant (live-API failure falls back to the
mock). Full detail in [DESIGN.md](DESIGN.md).

## Evaluation (summary)

40 automated tests (all passing offline), golden-dataset top-1 6/8 / top-3 8/8,
average confidence 0.93, and a documented human-evaluation table (5 pass / 2
partial / 0 fail). Full write-up in [EVALUATION.md](EVALUATION.md).
