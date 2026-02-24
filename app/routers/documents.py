"""
Documents router: upload, list, delete.

Architecture Decision:
- File upload is synchronous at the API level but indexing is async
- Status field tracks the indexing pipeline: pending → processing → indexed | failed
- Soft delete: file removed from disk and vectors, DB record preserved
"""

import asyncio
import uuid

import structlog
from fastapi import APIRouter, Depends, File, Request, UploadFile, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, AuthorizationError
from app.core.security import TokenData, get_current_user
from app.rag_engine.engine import delete_document_vectors, index_document
from app.repositories.repositories import AuditRepository, DocumentRepository
from app.schemas.schemas import DocumentListResponse, DocumentResponse
from app.utils.file_handler import delete_file, save_upload_file

router = APIRouter()
logger = structlog.get_logger(__name__)

# Limit concurrent indexing jobs to 1, preventing concurrent embedding API bursts
# that would exceed the 100 RPM free-tier limit
_indexing_semaphore = asyncio.Semaphore(1)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document for RAG indexing",
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and index a document.
    Returns 202 Accepted — document is queued for indexing asynchronously.
    Poll GET /documents to check indexing status.
    """
    doc_repo = DocumentRepository(db)
    audit_repo = AuditRepository(db)

    # Validate and save file to disk
    stored_filename, file_path, mime_type, file_size = await save_upload_file(
        file, current_user.client_id
    )

    # Create DB record
    doc = await doc_repo.create(
        client_id=current_user.client_id,
        uploaded_by_id=current_user.user_id,
        original_filename=file.filename or "unknown",
        stored_filename=stored_filename,
        file_path=file_path,
        mime_type=mime_type,
        file_size_bytes=file_size,
    )

    await audit_repo.log(
        action="UPLOAD",
        client_id=current_user.client_id,
        user_id=current_user.user_id,
        resource_type="document",
        resource_id=str(doc.id),
        ip_address=request.headers.get("X-Forwarded-For"),
        request_id=getattr(request.state, "request_id", None),
        extra={"filename": file.filename, "size_bytes": file_size},
    )

    # Commit DB record before starting background indexing
    await db.commit()

    # Bounded background indexing — semaphore ensures only 1 indexing job at a time
    # to prevent concurrent embedding API bursts that exceed rate limits
    asyncio.create_task(
        _index_document_bounded(
            file_path=file_path,
            mime_type=mime_type,
            document_id=str(doc.id),
            client_id=str(current_user.client_id),
            original_filename=file.filename or "unknown",
        )
    )

    logger.info(
        "Document upload accepted",
        document_id=str(doc.id),
        client_id=str(current_user.client_id),
    )

    return doc


async def _index_document_bounded(
    file_path: str,
    mime_type: str,
    document_id: str,
    client_id: str,
    original_filename: str,
) -> None:
    """Acquire the indexing semaphore before running the actual indexing task."""
    logger.info(
        "Indexing job queued, waiting for semaphore",
        document_id=document_id,
    )
    async with _indexing_semaphore:
        logger.info(
            "Indexing semaphore acquired, starting indexing",
            document_id=document_id,
        )
        await _index_document_background(
            file_path=file_path,
            mime_type=mime_type,
            document_id=document_id,
            client_id=client_id,
            original_filename=original_filename,
        )


async def _index_document_background(
    file_path: str,
    mime_type: str,
    document_id: str,
    client_id: str,
    original_filename: str,
) -> None:
    """
    Background task: index document into ChromaDB.
    Uses a separate DB session since the request session is closed.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        doc_repo = DocumentRepository(db)
        try:
            # Update status to processing
            await doc_repo.update_status(uuid.UUID(document_id), "processing")
            await db.commit()

            # Run the actual indexing (expensive — runs in thread pool)
            chunk_count = await index_document(
                file_path=file_path,
                mime_type=mime_type,
                document_id=document_id,
                client_id=client_id,
                original_filename=original_filename,
            )

            # Mark as indexed
            await doc_repo.update_status(
                uuid.UUID(document_id), "indexed", chunk_count=chunk_count
            )
            await db.commit()
            logger.info("Document indexed successfully", document_id=document_id)

        except Exception as e:
            logger.error("Document indexing failed", document_id=document_id, error=str(e))
            await doc_repo.update_status(
                uuid.UUID(document_id), "failed", error_message=str(e)[:500]
            )
            await db.commit()


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents for current client",
)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all non-deleted documents for the authenticated user's client."""
    doc_repo = DocumentRepository(db)
    documents, total = await doc_repo.list_by_client(
        current_user.client_id, page=page, page_size=page_size
    )
    return DocumentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=documents,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete document from DB, delete file from disk, delete vectors from ChromaDB.
    Enforces client isolation: users can only delete their own client's documents.
    """
    doc_repo = DocumentRepository(db)
    audit_repo = AuditRepository(db)

    doc = await doc_repo.get_by_id_and_client(document_id, current_user.client_id)
    if not doc:
        raise NotFoundError("Document", document_id)

    file_path = doc.file_path
    client_id = str(doc.client_id)

    # Soft delete in DB
    await doc_repo.soft_delete(document_id)

    await audit_repo.log(
        action="DELETE_DOC",
        client_id=current_user.client_id,
        user_id=current_user.user_id,
        resource_type="document",
        resource_id=str(document_id),
        ip_address=request.headers.get("X-Forwarded-For"),
        request_id=getattr(request.state, "request_id", None),
    )

    # Delete physical file
    delete_file(file_path)

    # Delete vectors asynchronously (non-blocking)
    asyncio.create_task(
        delete_document_vectors(str(document_id), client_id)
    )

    logger.info(
        "Document deleted",
        document_id=str(document_id),
        client_id=client_id,
    )
