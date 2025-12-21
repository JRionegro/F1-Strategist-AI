"""
Configuration loader for RAG components.

Loads vector store and embeddings configuration from environment.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from config/ directory
config_dir = Path(__file__).parent.parent.parent / "config"
load_dotenv(config_dir / ".env")


def get_chromadb_config() -> dict:
    """
    Get ChromaDB configuration from environment.

    Returns:
        Dictionary with ChromaDB configuration

    Environment variables:
        - CHROMADB_PATH: Directory to persist ChromaDB data
        - EMBEDDINGS_MODEL: Sentence-transformers model name
        - EMBEDDINGS_DEVICE: Device for embeddings (cpu or cuda)
    """
    return {
        "persist_directory": os.getenv(
            "CHROMADB_PATH",
            "./data/chromadb"
        ),
        "embeddings_model": os.getenv(
            "EMBEDDINGS_MODEL",
            "all-MiniLM-L6-v2"
        ),
        "embeddings_device": os.getenv(
            "EMBEDDINGS_DEVICE",
            "cpu"
        ),
        "collection_name": "f1_data"
    }


def get_vector_store_provider() -> str:
    """
    Get configured vector store provider.

    Returns:
        Vector store provider name ('chromadb' or 'pinecone')
    """
    return os.getenv("VECTOR_STORE_PROVIDER", "chromadb")
