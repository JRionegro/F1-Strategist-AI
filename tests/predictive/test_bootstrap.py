"""Tests for pit policy bootstrap (Phase 4A)."""

from __future__ import annotations

from typing import cast

from src.predictive.bootstrap import bootstrap_pit_policy_context
from src.predictive.schemas import PitPolicyContext
from src.rag.rag_manager import RAGManager
from src.rag.vector_store import SearchResult


class _FakeVectorStore:
    def __init__(self, results=None, all_docs=None):
        self._results = results or []
        self._all_docs = all_docs or []

    def search(self, query, k=5, filter_metadata=None):  # noqa: D401
        return self._results

    def get_all_documents(self):  # noqa: D401
        return self._all_docs


class _FakeRAGManager:
    def __init__(self, loaded: bool = True, vector_store=None):
        self._loaded = loaded
        self.vector_store = vector_store or _FakeVectorStore()

    def is_context_loaded(self) -> bool:
        return self._loaded


def test_bootstrap_returns_empty_when_context_not_loaded() -> None:
    manager = _FakeRAGManager(loaded=False)
    ctx = bootstrap_pit_policy_context(cast(RAGManager, manager))
    assert isinstance(ctx, PitPolicyContext)
    assert ctx.pit_policy_notes == ""
    assert ctx.source is None


def test_bootstrap_uses_strategy_doc_when_available() -> None:
    vs = _FakeVectorStore(
        results=[
            SearchResult(
                content="Pit rules",
                metadata={"filename": "strategy.md", "source": "global/strategy.md"},
                score=1.0,
                id="doc-1",
            )
        ]
    )
    manager = _FakeRAGManager(vector_store=vs)

    ctx = bootstrap_pit_policy_context(cast(RAGManager, manager))

    assert ctx.pit_policy_notes == "Pit rules"
    assert ctx.source == "global/strategy.md"
