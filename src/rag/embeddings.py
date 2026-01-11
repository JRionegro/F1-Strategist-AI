"""
Embeddings provider using sentence-transformers.

Wraps the all-MiniLM-L6-v2 model for generating text embeddings.
"""

import logging
from typing import Any

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from src.utils.logging_config import get_logger, LogCategory

# Use categorized logger for RAG/embeddings
logger = get_logger(LogCategory.RAG)


class EmbeddingsProvider:
    """Provides embeddings using sentence-transformers."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        """
        Initialize embeddings provider.

        Args:
            model_name: Name of the sentence-transformers model
            device: Device to run model on ('cpu' or 'cuda')

        Raises:
            ImportError: If sentence-transformers not installed
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name
        self.device = device

        logger.info(
            f"Loading embeddings model: {model_name} on {device}"
        )
        self.model = SentenceTransformer(model_name, device=device)  # type: ignore
        logger.info(f"Model loaded: {model_name}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple documents.

        Args:
            texts: List of text documents

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """
        Generate embedding for a single query.

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embedding.tolist()

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Embedding dimension
        """
        dim = self.model.get_sentence_embedding_dimension()
        return dim if dim is not None else 0

    def get_model_info(self) -> dict[str, Any]:
        """
        Get model information.

        Returns:
            Dictionary with model details
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "dimension": self.get_embedding_dimension(),
            "max_seq_length": self.model.max_seq_length
        }
