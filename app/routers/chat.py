"""
Chat router: submit RAG queries and get answers.
"""

import time
import uuid

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.rag_engine.engine import query_documents
from app.repositories.repositories import AuditRepository, QueryRepository
from app.schemas.schemas import ChatQueryRequest, ChatQueryResponse, SourceDocument

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Query documents using RAG",
)
async def query(
    body: ChatQueryRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a question against the client's indexed documents.
    Returns an AI-generated answer with source attribution.

    The question is sanitized for prompt injection before being passed to the LLM.
    """
    query_repo = QueryRepository(db)
    audit_repo = AuditRepository(db)

    # Create pending query record
    db_query = await query_repo.create(
        client_id=current_user.client_id,
        user_id=current_user.user_id,
        question=body.question,
    )
    await db.commit()

    start_time = time.monotonic()

    try:
        # Run RAG pipeline
        answer, sources, tokens_used = await query_documents(
            question=body.question,
            client_id=str(current_user.client_id),
        )

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Update query record with results
        await query_repo.complete(
            query_id=db_query.id,
            answer=answer,
            source_documents=sources,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

        await audit_repo.log(
            action="QUERY",
            client_id=current_user.client_id,
            user_id=current_user.user_id,
            resource_type="query",
            resource_id=str(db_query.id),
            ip_address=request.headers.get("X-Forwarded-For"),
            request_id=getattr(request.state, "request_id", None),
            extra={"tokens_used": tokens_used, "latency_ms": latency_ms},
        )

        # Format source documents for response
        source_items = [
            SourceDocument(
                document_id=s.get("document_id"),
                filename=s.get("filename"),
                page=s.get("page"),
                score=None,  # RetrievalQA doesn't expose scores directly
                excerpt=s.get("excerpt", ""),
            )
            for s in sources
        ]

        logger.info(
            "Query completed",
            query_id=str(db_query.id),
            client_id=str(current_user.client_id),
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

        return ChatQueryResponse(
            query_id=db_query.id,
            question=body.question,
            answer=answer,
            sources=source_items,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        await query_repo.fail(db_query.id, str(e)[:500])
        logger.error(
            "Query failed",
            query_id=str(db_query.id),
            error=str(e),
            latency_ms=latency_ms,
        )
        raise


@router.get(
    "/history",
    summary="Get query history for current client",
)
async def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated query history for the authenticated client."""
    query_repo = QueryRepository(db)
    queries, total = await query_repo.list_by_client(
        current_user.client_id, page=page, page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(q.id),
                "question": q.question,
                "answer": q.answer,
                "status": q.status,
                "tokens_used": q.tokens_used,
                "latency_ms": q.latency_ms,
                "created_at": q.created_at.isoformat(),
            }
            for q in queries
        ],
    }
