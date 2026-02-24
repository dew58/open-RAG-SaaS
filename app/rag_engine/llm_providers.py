"""
Pluggable LLM and Embedding provider interface.

Architecture Decision:
- Abstract base classes allow swapping providers via environment variable
- Factory functions read LLM_PROVIDER / EMBEDDING_PROVIDER from config
- Each provider encapsulates its own initialization logic
- Adding a new provider = one new class + one entry in the factory dict

Supported providers:
- LLM:       gemini (Google Gemma 3 12B)
- Embedding: gemini (Google gemini-embedding-001), ollama (nomic-embed-text)
"""

import logging
from abc import ABC, abstractmethod

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_ollama import OllamaEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Abstract Interfaces ──────────────────────────────────────────────────────


class LLMProvider(ABC):
    """Abstract base for LLM chat providers."""

    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """Return a LangChain chat model instance."""
        ...


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    def get_embeddings(self) -> Embeddings:
        """Return a LangChain embeddings instance."""
        ...


# ── Gemini Providers ─────────────────────────────────────────────────────────


class GeminiLLMProvider(LLMProvider):
    """Google Gemma 3 12B LLM provider."""

    def get_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.GEMINI_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_TOKENS,
        )


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google gemini-embedding-001 provider."""

    def get_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        return GoogleGenerativeAIEmbeddings(
            model=settings.GEMINI_EMBEDDING_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
        )


# ── Ollama Providers ─────────────────────────────────────────────────────────


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama local embedding provider (e.g. nomic-embed-text)."""

    def get_embeddings(self) -> OllamaEmbeddings:
        return OllamaEmbeddings(
            model=settings.OLLAMA_EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )


# ── Factory Functions ─────────────────────────────────────────────────────────

_LLM_PROVIDERS = {
    "gemini": GeminiLLMProvider,
}

_EMBEDDING_PROVIDERS = {
    "gemini": GeminiEmbeddingProvider,
    "ollama": OllamaEmbeddingProvider,
}


def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider.
    Reads LLM_PROVIDER from settings (default: "gemini").
    """
    provider_name = settings.LLM_PROVIDER.lower()
    provider_class = _LLM_PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider_name}'. "
            f"Available: {list(_LLM_PROVIDERS.keys())}"
        )
    logger.info(f"Using LLM provider: {provider_name}")
    return provider_class()


def get_embedding_provider() -> EmbeddingProvider:
    """
    Get the configured embedding provider.
    Reads EMBEDDING_PROVIDER from settings (default: "gemini").
    """
    provider_name = settings.EMBEDDING_PROVIDER.lower()
    provider_class = _EMBEDDING_PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER: '{provider_name}'. "
            f"Available: {list(_EMBEDDING_PROVIDERS.keys())}"
        )
    logger.info(f"Using embedding provider: {provider_name}")
    return provider_class()
