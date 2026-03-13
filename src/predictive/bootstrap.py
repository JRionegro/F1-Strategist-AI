"""Bootstrap helpers for predictive AI.

Loads pit-decision guidance from the RAG corpus once per simulation.
"""

from __future__ import annotations

from typing import Optional

from src.predictive.schemas import PitPolicyContext
from src.rag.rag_manager import RAGManager
from src.utils.logging_config import get_logger, LogCategory
from src.rag.vector_store import SearchResult

logger = get_logger(LogCategory.RAG)


def _extract_source(metadata: dict | None) -> Optional[str]:
    if not metadata:
        return None
    return metadata.get("source") or metadata.get("filename")


def bootstrap_pit_policy_context(rag_manager: RAGManager) -> PitPolicyContext:
    """Load pit/no-pit guidance from strategy.md via RAG.

    The lookup is designed to run exactly once per simulation start. It returns
    an empty-but-well-formed context when the RAG corpus is not loaded or the
    file is missing.
    """
    if rag_manager is None:
        logger.warning(
            "RAG manager missing; returning empty pit policy context")
        return PitPolicyContext()

    try:
        if not rag_manager.is_context_loaded():
            logger.warning(
                "RAG context not loaded; returning empty pit policy context")
            return PitPolicyContext()
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG context check failed: %s", exc)
        return PitPolicyContext()

    # Primary: vector search filtered to strategy.md
    try:
        results = rag_manager.vector_store.search(
            query="pit stop decision rules",
            k=1,
            filter_metadata={"filename": "strategy.md"},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pit policy search failed: %s", exc)
        results = []

    if results:
        top: SearchResult | dict = results[0]
        if isinstance(top, SearchResult):
            return PitPolicyContext(
                pit_policy_notes=(top.content or "").strip(),
                source=_extract_source(top.metadata),
            )
        # Support dict-shaped fallbacks
        metadata = top.get("metadata", {}) if isinstance(top, dict) else {}
        content = top.get("content", "") if isinstance(top, dict) else ""
        return PitPolicyContext(
            pit_policy_notes=str(content).strip(),
            source=_extract_source(metadata),
        )

    # Fallback: scan all documents for strategy.md (first match)
    try:
        all_docs = rag_manager.vector_store.get_all_documents()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallback document scan failed: %s", exc)
        return PitPolicyContext()

    for doc in all_docs:
        metadata = doc.get("metadata", {})
        if metadata.get("filename") == "strategy.md":
            return PitPolicyContext(
                pit_policy_notes=str(doc.get("content", "")).strip(),
                source=_extract_source(metadata),
            )

    # Not found
    logger.info("strategy.md not found in RAG; using empty pit policy context")
    return PitPolicyContext()
