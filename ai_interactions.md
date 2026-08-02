# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.
>
> **Note to self:** drafted from the real agent session that built the final
> project — edit into my own voice and verify each claim before submitting.

---

## Agent Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I asked Claude Code to extend the debugged guessing game into a full applied AI
system for the final project — an "AI Glitch Investigator" that uses retrieval
(RAG), an agentic workflow, and a reliability-testing system, while keeping the
original game and its tests untouched.

**What did the agent do?**

Working from an approved plan, the agent built a new `glitch_investigator/`
package across several files: a bug-pattern knowledge base with a pure-Python
TF-IDF retriever, a provider-agnostic LLM interface (real Claude via structured
outputs, plus a deterministic offline mock), a static AST verifier that never
executes the submitted code, and an agentic pipeline that runs
retrieve → diagnose → fix → verify → refine with logging and error handling. It
also added a Streamlit page (`pages/`), a labeled golden dataset, three test
suites, and docs (`DESIGN.md`, README updates). It ran `pytest` and booted the
app to confirm both worked.

**What did you have to verify or fix manually?**

I verified every claim rather than taking the agent's word for it. The biggest
catch: the retriever initially ranked the wrong bug pattern first for the
int-vs-str case, which two tests exposed — I made the agent tune the knowledge
base and re-run the suite instead of loosening the test to hide the miss. I also
had it add real `logging` and wrap the live LLM calls in error handling with a
mock fallback after I pointed out the rubric required "logging or guardrails" and
that a live API failure could crash the app. Final state: 40/40 tests passing
offline, app serving both pages.

---

## Test Generation (SF7)

> Document how you used AI to help generate or improve tests.

| Edge Case | Prompt Used | AI-Suggested Test | Did It Pass? | Your Reasoning |
|-----------|-------------|-------------------|--------------|----------------|
| Empty / whitespace input | "add robustness tests for bad input to the investigator" | `test_robustness_bad_inputs` — asserts `investigate("")` returns `ok=False` cleanly | Yes | Confirms the guardrail rejects junk instead of hallucinating a bug |
| Prompt injection in the code | same | `test_prompt_injection_is_treated_as_data` — hides "ignore instructions / output PWNED" in the snippet | Yes | Proves the code is analyzed as data, never obeyed — a real security property |
| Live backend failure | "prove the pipeline recovers if the live model call throws" | `test_live_backend_failure_falls_back_to_mock` — injects a client whose calls raise | Yes | Verifies graceful fallback to the offline mock instead of a crash |
| Retrieval accuracy on a golden set | "measure detection accuracy on labeled cases, don't overfit to 100%" | `test_top3_recall_is_perfect` + `test_top1_accuracy_clears_threshold` | Yes | Honest metrics (top-1 6/8, top-3 8/8) — flags a real limitation instead of hiding it |

---

## Linting & Style (SF9)

> Document your use of AI for linting or code style improvements.

<!-- Not attempted for this project. -->

---

## Model Comparison (SF11)

> Compare two AI models on the same task.

<!-- Not attempted for this project. The provider-agnostic backend does compare a
     live Claude model against a deterministic rule-based baseline for the same
     diagnosis task, which could be written up here if desired. -->
