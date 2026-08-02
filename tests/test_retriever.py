"""Tests for the RAG retrieval layer (Module 4)."""

from glitch_investigator.knowledge_base import KnowledgeBase, tokenize


def test_tokenize_splits_snake_and_camel_case():
    toks = tokenize("st.session_state.getValue")
    assert "session" in toks
    assert "state" in toks
    assert "value" in toks  # camelCase split


def test_tokenize_drops_stopwords_and_short_tokens():
    toks = tokenize("if the a return")
    assert toks == []  # all stopwords / too short


def test_retrieve_ranks_state_bug_first():
    kb = KnowledgeBase.load()
    code = "secret = random.randint(1, 100)\nif st.button('go'):\n    st.write(secret)"
    top = kb.retrieve(code, k=3)
    assert top, "should retrieve at least one pattern"
    assert top[0].pattern.id == "streamlit-state-reset"
    assert top[0].score > 0
    assert top[0].matched_terms  # transparency: we can see why it matched


def test_retrieve_returns_scores_in_descending_order():
    kb = KnowledgeBase.load()
    results = kb.retrieve("guess > str(secret) too high too low win", k=3)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_unrelated_text_retrieves_nothing_or_low():
    kb = KnowledgeBase.load()
    # Prose with no bug signal should surface no confident match.
    results = kb.retrieve("cats and weather and holiday plans", k=3)
    assert results == [] or results[0].score < 0.1


def test_get_by_id():
    kb = KnowledgeBase.load()
    assert kb.get("int-str-compare").name.startswith("Comparing")
    assert kb.get("does-not-exist") is None
