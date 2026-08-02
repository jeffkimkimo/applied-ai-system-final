"""Knowledge base + retriever — the RAG (retrieval) layer (Module 4).

The retriever is intentionally pure Python (no embeddings API, no heavy deps) so
the system runs and is graded fully offline. It scores each bug-pattern document
against the pasted code using token-overlap cosine similarity with inverse
document frequency (IDF) weighting — a compact, transparent TF-IDF retriever.

Transparency is a trustworthiness feature: every retrieval returns a numeric
score and the matched tokens, so a human can see *why* a pattern was surfaced.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

_DATA_PATH = Path(__file__).parent / "data" / "bug_patterns.json"

# Tokens that carry no signal for bug retrieval; ignored during scoring.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "on", "for",
    "if", "else", "elif", "return", "def", "self", "with", "as", "not", "be",
    "this", "that", "should", "when", "every", "each", "was", "are", "at",
}

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def tokenize(text: str) -> List[str]:
    """Lowercase identifier/word tokens, stopwords removed.

    Snake_case and camelCase are split so 'st.session_state' and 'sessionState'
    both surface the 'session' / 'state' signal.
    """
    if not text:
        return []
    raw = _TOKEN_RE.findall(text)
    tokens: List[str] = []
    for tok in raw:
        # split snake_case
        parts = tok.split("_")
        for part in parts:
            # split camelCase
            for sub in re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", part) or [part]:
                low = sub.lower()
                if low and low not in _STOPWORDS and len(low) > 1:
                    tokens.append(low)
    return tokens


@dataclass(frozen=True)
class BugPattern:
    """One retrievable document in the knowledge base."""

    id: str
    name: str
    symptom: str
    cause: str
    fix: str
    signals: Tuple[str, ...]
    keywords: str
    example: str

    @property
    def document(self) -> str:
        """The text that represents this pattern for retrieval."""
        return " ".join([
            self.name, self.symptom, self.cause, self.fix,
            " ".join(self.signals), self.keywords, self.example,
        ])


@dataclass
class RetrievedPattern:
    """A pattern plus its retrieval score and the tokens that matched."""

    pattern: BugPattern
    score: float
    matched_terms: List[str] = field(default_factory=list)


class KnowledgeBase:
    """Loads the corpus and retrieves the most relevant patterns for code.

    Uses TF-IDF cosine similarity computed with the standard library only.
    """

    def __init__(self, patterns: List[BugPattern]):
        self.patterns = patterns
        self._doc_tokens = [tokenize(p.document) for p in patterns]
        self._idf = self._compute_idf(self._doc_tokens)
        self._doc_vectors = [self._tfidf(toks) for toks in self._doc_tokens]

    # ---- construction ----
    @classmethod
    def load(cls, path: Path | str = _DATA_PATH) -> "KnowledgeBase":
        data = json.loads(Path(path).read_text())
        patterns = [
            BugPattern(
                id=p["id"],
                name=p["name"],
                symptom=p["symptom"],
                cause=p["cause"],
                fix=p["fix"],
                signals=tuple(p.get("signals", [])),
                keywords=p.get("keywords", ""),
                example=p.get("example", ""),
            )
            for p in data["patterns"]
        ]
        return cls(patterns)

    # ---- scoring internals ----
    @staticmethod
    def _compute_idf(doc_tokens: List[List[str]]) -> dict:
        n_docs = len(doc_tokens)
        df: dict = {}
        for toks in doc_tokens:
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        # Smoothed IDF so a term in every doc still contributes a little.
        return {
            term: math.log((1 + n_docs) / (1 + count)) + 1.0
            for term, count in df.items()
        }

    def _tfidf(self, tokens: List[str]) -> dict:
        if not tokens:
            return {}
        tf: dict = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        n = len(tokens)
        return {
            term: (count / n) * self._idf.get(term, 1.0)
            for term, count in tf.items()
        }

    @staticmethod
    def _cosine(a: dict, b: dict) -> Tuple[float, List[str]]:
        if not a or not b:
            return 0.0, []
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0, []
        return dot / (na * nb), sorted(common)

    # ---- public API ----
    def retrieve(self, code: str, k: int = 3) -> List[RetrievedPattern]:
        """Return the top-k patterns most relevant to `code`, ranked by score.

        Patterns with a zero score are dropped, so an unrelated snippet returns
        fewer (or no) results rather than noise — this powers abstention.
        """
        query_vec = self._tfidf(tokenize(code))
        scored: List[RetrievedPattern] = []
        for pattern, doc_vec in zip(self.patterns, self._doc_vectors):
            score, matched = self._cosine(query_vec, doc_vec)
            if score > 0:
                scored.append(RetrievedPattern(pattern, round(score, 4), matched))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:k]

    def get(self, pattern_id: str) -> BugPattern | None:
        for p in self.patterns:
            if p.id == pattern_id:
                return p
        return None
