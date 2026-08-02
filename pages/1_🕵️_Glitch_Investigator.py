"""Streamlit page: the AI Glitch Investigator.

Paste buggy Python / Streamlit code (or load a preset — including the original
glitchy guessing game) and the AI investigates it: it retrieves similar known
bug patterns (RAG), reasons about the fault with cited evidence, proposes a fix,
and statically verifies its own answer — showing every step of the agent trace.
"""

import logging

import streamlit as st

from glitch_investigator import investigate, KnowledgeBase, get_client
from glitch_investigator.llm import _has_credentials

# Surface the pipeline's logs in the console the app runs in — every
# investigation logs retrieval, diagnosis, fix/verify attempts, and any live
# backend errors it recovered from.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(page_title="AI Glitch Investigator", page_icon="🕵️")

# Preset snippets. The first is the *original* glitchy game — the thing you
# hand-debugged in Module 1, now handed to the AI that would do it for you.
PRESETS = {
    "Original glitchy game (state + compare + hint bugs)": (
        "import streamlit as st\n"
        "import random\n\n"
        "# The AI that wrote this claimed it was production-ready.\n"
        "secret = random.randint(1, 100)\n\n"
        "guess = st.number_input('Your guess', step=1)\n"
        "attempt = st.session_state.get('attempt', 1)\n\n"
        "if st.button('Submit'):\n"
        "    if attempt % 2 == 0:\n"
        "        secret = str(secret)\n"
        "    if guess > secret:\n"
        "        st.write('Too high — go HIGHER!')\n"
        "    elif guess < secret:\n"
        "        st.write('Too low — go LOWER!')\n"
        "    else:\n"
        "        st.write('You win!')\n"
    ),
    "Backwards hint only": (
        "def hint(guess, secret):\n"
        "    if guess > secret:\n"
        "        return 'Too high, go HIGHER!'\n"
        "    return 'Too low, go LOWER!'\n"
    ),
    "Erratic scoring": (
        "import random\n"
        "if outcome != 'Win':\n"
        "    score += random.choice([-5, 5])\n"
    ),
    "(blank — paste your own)": "",
}


def _sidebar():
    st.sidebar.header("AI backend")
    live = _has_credentials()
    if live:
        st.sidebar.success("Claude live — real model reasoning")
    else:
        st.sidebar.info("Offline mock — deterministic, no API key")
    st.sidebar.caption(
        "The system is provider-agnostic: it uses Claude when `ANTHROPIC_API_KEY` "
        "is set, and a deterministic rule-based mock otherwise. Everything below "
        "runs either way."
    )
    st.sidebar.divider()
    st.sidebar.caption("**Why you can trust it**")
    st.sidebar.markdown(
        "- Every claim is grounded in retrieved patterns + cited lines\n"
        "- It **abstains** when unsure instead of guessing\n"
        "- It **never executes** your code — verification is static (AST)\n"
        "- Your code is treated as data, never as instructions\n"
        "- You review the diff; nothing is auto-applied"
    )


st.title("🕵️ AI Glitch Investigator")
st.caption(
    "You hand-debugged the glitchy game in Module 1. This is the AI that "
    "investigates glitches for you — retrieve, reason, fix, and verify."
)
_sidebar()

preset = st.selectbox("Load a preset, or paste your own below:", list(PRESETS))
code = st.text_area("Code to investigate", value=PRESETS[preset], height=280)

if st.button("🔍 Investigate", type="primary"):
    with st.spinner("Investigating…"):
        result = investigate(code)

    st.caption(f"Backend: **{result.backend}**")

    if not result.ok:
        st.error(result.message)
        st.stop()

    # 1. Retrieval (RAG)
    st.subheader("1. Retrieved bug patterns (RAG)")
    if result.retrieved:
        st.table(
            {
                "pattern": [r.pattern.id for r in result.retrieved],
                "score": [r.score for r in result.retrieved],
                "name": [r.pattern.name for r in result.retrieved],
            }
        )
    else:
        st.write("No patterns retrieved.")

    # 2. Reasoned diagnosis
    st.subheader("2. Diagnosis (reasoning)")
    d = result.diagnosis
    if d.abstained:
        st.warning(
            "🤔 The Investigator **abstained** — no known pattern matched with "
            "enough confidence. It won't guess."
        )
    else:
        conf_pct = int(d.confidence * 100)
        st.markdown(f"**Bug:** {d.bug_name}")
        st.progress(min(1.0, d.confidence), text=f"Confidence: {conf_pct}%")
        st.write(d.explanation)
        if d.evidence_lines:
            st.caption(f"Evidence — cited lines: {d.evidence_lines}")

    # 3. Proposed fix + diff
    if result.fix and result.fix.changed:
        st.subheader("3. Proposed fix (review before applying)")
        st.write(result.fix.summary)
        if result.diff:
            st.code(result.diff, language="diff")

    # 4. Verification
    if result.verification:
        st.subheader("4. Self-verification (static, no code executed)")
        v = result.verification
        (st.success if v.passed else st.error)(v.summary)
        for c in v.checks:
            st.write(("✅ " if c.passed else "❌ ") + f"**{c.name}** — {c.detail}")
        if result.refinements:
            st.caption(f"Refinement loop ran {result.refinements} extra time(s).")

    # Agent trace (auditability)
    with st.expander("Full agent trace"):
        for step in result.trace:
            st.write(f"**{step.name}** — {step.detail}")

    st.divider()
    st.caption(result.message)
