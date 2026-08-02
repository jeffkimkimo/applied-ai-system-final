"""AI Glitch Investigator.

An applied AI system that investigates buggy Python / Streamlit code the way a
developer debugs by hand: it *retrieves* similar known bug patterns (RAG),
*reasons* about the fault with cited evidence, proposes a fix, and *verifies*
its own answer in a bounded agentic loop.

Public surface:
    investigate(code)         -> InvestigationResult   (the full agentic pipeline)
    KnowledgeBase             -> the retrievable bug-pattern corpus (RAG)
    get_client()              -> an LLMClient (real Claude, or a deterministic mock)
"""

from .knowledge_base import KnowledgeBase, BugPattern
from .llm import get_client, LLMClient, MockClient, backend_name
from .agent import investigate, InvestigationResult

__all__ = [
    "investigate",
    "InvestigationResult",
    "KnowledgeBase",
    "BugPattern",
    "get_client",
    "LLMClient",
    "MockClient",
    "backend_name",
]
