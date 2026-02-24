"""
RAG (Retrieval-Augmented Generation) engine.

Architecture Decisions:
- ChromaDB PersistentClient: survives restarts, one collection per tenant
- asyncio.Lock per client_id: prevents race conditions during concurrent indexing
- run_in_executor for ChromaDB sync calls: prevents blocking the event loop
- RecursiveCharacterTextSplitter: better than CharacterTextSplitter for
  preserving semantic boundaries
- Custom system prompt framing reduces prompt injection risk
- Pluggable LLM and embedding providers via llm_providers module
"""

import asyncio
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.chains import RetrievalQA
from langchain.schema import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_community.vectorstores import Chroma

from app.core.config import settings
from app.core.exceptions import RagPipelineError
from app.rag_engine.llm_providers import get_embedding_provider, get_llm_provider
from app.rag_engine.api_rate_limiter import embedding_rate_limiter, llm_rate_limiter

logger = structlog.get_logger(__name__)

# Thread pool for running sync ChromaDB/LangChain operations
# without blocking the async event loop.
# max_workers=1 ensures strictly sequential API calls to respect rate limits.
_executor = ThreadPoolExecutor(max_workers=1)

# Per-client locks prevent concurrent indexing from corrupting the same collection
_client_locks: Dict[str, asyncio.Lock] = {}
_locks_mutex = asyncio.Lock()


async def get_client_lock(client_id: str) -> asyncio.Lock:
    """Get or create a per-client async lock for safe concurrent access."""
    async with _locks_mutex:
        if client_id not in _client_locks:
            _client_locks[client_id] = asyncio.Lock()
        return _client_locks[client_id]


def get_collection_name(client_id: uuid.UUID) -> str:
    """
    Deterministic, tenant-isolated collection name.
    Chroma collection names: alphanumeric + underscores, 3-63 chars.
    """
    return f"client_{str(client_id).replace('-', '_')}"


# ── ChromaDB Client (Singleton) ───────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """
    Singleton ChromaDB client.
    PersistentClient writes to disk, survives restarts.
    lru_cache ensures one client regardless of how many threads call this.
    """
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=False,  # Prevent accidental data loss in production
        ),
    )
    logger.info("ChromaDB client initialized", persist_dir=str(persist_dir))
    return client


def get_embeddings():
    """
    Get embeddings from the configured provider.
    Provider is selected via EMBEDDING_PROVIDER env var.
    Default: Gemini gemini-embedding-001
    Alternative: Ollama nomic-embed-text (set EMBEDDING_PROVIDER=ollama)
    """
    provider = get_embedding_provider()
    return provider.get_embeddings()


def get_llm():
    """
    Get LLM from the configured provider.
    Provider is selected via LLM_PROVIDER env var.
    Default: Google Gemma 3 12B (gemma-3-12b-it)
    """
    provider = get_llm_provider()
    return provider.get_llm()


# ── Document Loading ──────────────────────────────────────────────────────────

def load_document(file_path: str, mime_type: str) -> List[LangchainDocument]:
    """
    Load document from disk using appropriate LangChain loader.
    Returns a list of LangchainDocuments (one per page for PDFs).
    """
    loaders = {
        "application/pdf": PyPDFLoader,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": Docx2txtLoader,
        "text/plain": TextLoader,
    }

    loader_class = loaders.get(mime_type)
    if not loader_class:
        raise RagPipelineError(f"Unsupported MIME type: {mime_type}")

    if not os.path.exists(file_path):
        raise RagPipelineError(f"File not found: {file_path}")

    try:
        if mime_type == "text/plain":
            loader = loader_class(file_path, encoding="utf-8", autodetect_encoding=True)
        else:
            loader = loader_class(file_path)
        return loader.load()
    except Exception as e:
        raise RagPipelineError(f"Failed to load document: {str(e)}")


def split_documents(
    documents: List[LangchainDocument],
    document_id: str,
    client_id: str,
    original_filename: str,
) -> List[LangchainDocument]:
    """
    Split documents into chunks with tenant-scoped metadata.

    Metadata stored with each chunk enables:
    - Source attribution in responses
    - Filtered retrieval by document
    - Tenant isolation verification at retrieval time
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_documents(documents)

    # Enrich chunks with metadata for retrieval attribution
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "document_id": document_id,
            "client_id": client_id,
            "filename": original_filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
        })

    return chunks


# ── Indexing ──────────────────────────────────────────────────────────────────

def _index_document_sync(
    file_path: str,
    mime_type: str,
    document_id: str,
    client_id: str,
    original_filename: str,
) -> int:
    """
    Synchronous indexing function. Run via executor to avoid blocking event loop.
    Returns number of chunks indexed.
    """
    collection_name = get_collection_name(uuid.UUID(client_id))

    # Load and split
    raw_docs = load_document(file_path, mime_type)
    chunks = split_documents(raw_docs, document_id, client_id, original_filename)

    if not chunks:
        raise RagPipelineError("Document produced no text content after splitting")

    # Build LangChain Chroma wrapper with our persistent client
    chroma_client = get_chroma_client()
    embeddings = get_embeddings()

    vectorstore = Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
    )

    # Add documents in rate-limited batches to respect embedding API limits
    batch_size = settings.EMBEDDING_BATCH_SIZE
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    embedding_rate_limiter.reset_counter()

    logger.info(
        "Starting rate-limited embedding",
        document_id=document_id,
        total_chunks=len(chunks),
        batch_size=batch_size,
        total_batches=total_batches,
    )

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        ids = [f"{document_id}_{j + i}" for j in range(len(batch))]

        # Rate limit: wait before each embedding API call
        embedding_rate_limiter.wait()

        vectorstore.add_documents(batch, ids=ids)

        embedding_rate_limiter.log_request_complete(
            input_tokens=sum(len(c.page_content.split()) for c in batch),
            extra={"batch": f"{batch_num}/{total_batches}", "chunk_count": len(batch)},
        )

    logger.info(
        "Document indexed",
        document_id=document_id,
        client_id=client_id,
        chunk_count=len(chunks),
        embedding_requests=embedding_rate_limiter.total_requests,
    )
    return len(chunks)


async def index_document(
    file_path: str,
    mime_type: str,
    document_id: str,
    client_id: str,
    original_filename: str,
) -> int:
    """
    Async wrapper for document indexing.
    Uses per-client lock to prevent concurrent writes to same collection.
    """
    lock = await get_client_lock(client_id)

    async with lock:
        loop = asyncio.get_event_loop()
        try:
            chunk_count = await loop.run_in_executor(
                _executor,
                _index_document_sync,
                file_path,
                mime_type,
                document_id,
                client_id,
                original_filename,
            )
            return chunk_count
        except RagPipelineError:
            raise
        except Exception as e:
            logger.error(
                "Indexing failed",
                document_id=document_id,
                error=str(e),
                exc_info=True,
            )
            raise RagPipelineError(f"Indexing failed: {str(e)}")


# ── Retrieval ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based ONLY on the provided context documents.

Rules:
1. Answer based solely on the context provided below.
2. If the answer cannot be found in the context, say "I don't have enough information to answer this question based on the available documents."
3. Do not make up information or use knowledge outside the provided context.
4. Cite the source document when relevant.
5. Be concise and accurate.

Context:
{context}

Question: {question}

Answer:"""


def _query_sync(
    question: str,
    client_id: str,
    top_k: int = None,
) -> Tuple[str, List[dict], int]:
    """
    Synchronous RAG query. Runs via executor.
    Returns (answer, source_documents, tokens_used).
    """
    top_k = top_k or settings.RETRIEVAL_TOP_K
    collection_name = get_collection_name(uuid.UUID(client_id))

    chroma_client = get_chroma_client()
    embeddings = get_embeddings()
    llm = get_llm()

    # Create retriever scoped to this client's collection
    vectorstore = Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    # Verify collection has documents
    count = vectorstore._collection.count()
    if count == 0:
        return (
            "No documents have been uploaded yet. Please upload documents before querying.",
            [],
            0,
        )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k},
    )

    # RetrievalQA with custom prompt
    from langchain.prompts import PromptTemplate
    from langchain.chains import RetrievalQA

    prompt = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=["context", "question"],
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )

    # Rate limit: wait before LLM API call
    llm_rate_limiter.wait()

    result = qa_chain.invoke({"query": question})
    answer = result["result"]
    source_docs = result.get("source_documents", [])

    # Format source documents for response
    sources = []
    for doc in source_docs:
        meta = doc.metadata
        sources.append({
            "document_id": meta.get("document_id"),
            "filename": meta.get("filename"),
            "page": meta.get("page"),
            "chunk_index": meta.get("chunk_index"),
            "excerpt": doc.page_content[:500],  # Truncate for response size
        })

    # Approximate token counts for billing tracking
    input_tokens = len(question.split()) + sum(
        len(d.page_content.split()) for d in source_docs
    )
    output_tokens = len(answer.split())
    tokens_used = input_tokens + output_tokens

    llm_rate_limiter.log_request_complete(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        extra={"client_id": client_id},
    )

    return answer, sources, tokens_used


async def query_documents(
    question: str,
    client_id: str,
    top_k: Optional[int] = None,
) -> Tuple[str, List[dict], int]:
    """
    Async wrapper for RAG query.
    No per-client lock needed for reads — ChromaDB handles concurrent reads safely.
    """
    loop = asyncio.get_event_loop()
    try:
        answer, sources, tokens = await loop.run_in_executor(
            _executor,
            _query_sync,
            question,
            client_id,
            top_k,
        )
        return answer, sources, tokens
    except RagPipelineError:
        raise
    except Exception as e:
        logger.error("Query failed", client_id=client_id, error=str(e), exc_info=True)
        raise RagPipelineError(f"Query failed: {str(e)}")


# ── Cleanup ───────────────────────────────────────────────────────────────────

def _delete_document_vectors_sync(document_id: str, client_id: str) -> None:
    """Delete all vector chunks for a document from the client's collection."""
    collection_name = get_collection_name(uuid.UUID(client_id))
    chroma_client = get_chroma_client()

    try:
        collection = chroma_client.get_collection(collection_name)
        # Delete all chunks with this document_id
        collection.delete(where={"document_id": {"$eq": document_id}})
        logger.info("Vectors deleted", document_id=document_id, client_id=client_id)
    except Exception as e:
        # Collection may not exist (document never indexed successfully)
        logger.warning(
            "Vector deletion failed (may not exist)",
            document_id=document_id,
            error=str(e),
        )


async def delete_document_vectors(document_id: str, client_id: str) -> None:
    """Async wrapper for vector deletion."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor,
        _delete_document_vectors_sync,
        document_id,
        client_id,
    )
