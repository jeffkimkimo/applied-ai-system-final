# 💭 Reflection: Game Glitch Investigator

> **Note to self:** this is a first draft grounded in what actually happened in
> this repo (the bugs I fixed, the tests I wrote, and the final-project
> extension). Read each answer and edit it into my own voice — make sure every
> claim matches what I actually experienced before submitting.

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?
- List at least two concrete bugs you noticed at the start  
  (for example: "the hints were backwards").

The game ran, but it was unplayable. The secret number changed on every click
because it was recomputed at the top of the script on each Streamlit rerun, so
there was no stable target to guess. On top of that the hints were backwards —
guessing too high told me to "go HIGHER" — and on even attempts the secret was
cast to a string, so `guess > secret` compared an int to a str and produced
garbage. Scoring also jumped around because wrong guesses randomly added or
subtracted points.

**Bug Reproduction Log**

Document at least 3 bugs you found. Add rows as needed.

| Input | Expected Behavior | Actual Behavior | Console Output / Error |
|-------|-------------------|-----------------|------------------------|
| Click "Submit" twice with the same guess | Secret stays the same within a round | Secret changes every click (never winnable) | None — silent; visible only via the Debug panel |
| Guess higher than the secret | Hint: "Too high — go LOWER" | Hint: "go HIGHER" (reversed) | None — wrong output, no error |
| Any guess on an even-numbered attempt | int-vs-int comparison → correct hint | `int > str` comparison → wrong/garbage hint | Silent TypeError swallowed by fallback |

---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion that was incorrect or misleading (including what the AI suggested and how you verified the result).

I used Claude Code as an agent teammate to refactor the logic and, for the final
project, to design the AI Glitch Investigator. A correct suggestion: it proposed
moving the pure logic into `logic_utils.py` and asserting the fixes with pytest;
I verified it by running `pytest` and watching all 8 tests pass, including ones
that reproduced the original bugs. A misleading moment: the first version of the
knowledge-base retriever confidently ranked the "backwards hint" pattern above
the "int-vs-str" pattern for a snippet that had both, so the AI's top answer was
wrong. I caught it because my reliability test asserted the expected pattern per
case, and instead of trusting the AI I looked at the retrieval scores, saw the
vocabulary overlap, and tuned the corpus — then re-ran the tests to confirm.

---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

I decided a bug was fixed only when a test failed before the change and passed
after it — not just when the app "looked right." For example,
`test_update_score_wrong_guess_does_not_change_score` pins the score across wrong
guesses; it showed me that scoring is now a pure function of outcome and attempt
count, with no hidden randomness. For the final project I went further and built
a golden-dataset reliability test that runs the whole pipeline over labeled buggy
snippets and measures accuracy, which surfaced the honest limit that the
retriever gets the right pattern first only 6 out of 8 times (but always within
the top 3). AI helped me design the edge-case tests — empty input, non-code,
oversized input, and a prompt-injection string — which I then read through and
kept because each one caught a real failure mode.

---

## 4. What did you learn about Streamlit and state?

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?

Streamlit re-runs the entire script from top to bottom every time you touch a
widget — click a button, type in a box, anything. So a normal variable like
`secret = random.randint(1, 100)` is thrown away and recomputed on every
interaction, which is exactly why the secret kept changing. `st.session_state`
is the box that survives those reruns: you initialize a value in it once (guarded
by `if "secret" not in st.session_state`) and read/write it after that, so it
persists across clicks. The mental model that stuck with me is "the script is
stateless; session_state is the only memory."

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.

The habit I want to keep is writing a failing test first and only trusting a fix
once that test flips to green — it turned "I think it works" into "I can prove it
works," and it's what caught the AI's wrong retrieval ranking. Next time I'd
verify the AI's *claims* even earlier, especially confident-sounding ones, rather
than assuming a plausible answer is a correct one. This project changed how I see
AI-generated code: it's a fast, useful draft, but it can be confidently wrong in
silent ways, so it needs the same grounding, tests, and guardrails I'd demand of
my own code — which is exactly the philosophy I built into the Investigator
(cite your evidence, abstain when unsure, never trust untrusted input).
