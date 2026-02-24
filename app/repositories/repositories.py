"""
Repository pattern for database access.

Architecture Decision:
- Repository abstracts all SQL from service layer
- Each method returns domain objects, not raw SQL results
- Soft delete queries automatically filter out deleted records
- All writes use explicit transactions
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import AuditLog, Client, Document, Query, User

logger = structlog.get_logger(__name__)


# ── Client Repository ─────────────────────────────────────────────────────────

class ClientRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, slug: str, plan: str = "starter") -> Client:
        client = Client(name=name, slug=slug, plan=plan)
        self.db.add(client)
        await self.db.flush()  # Get ID without committing
        return client

    async def get_by_id(self, client_id: uuid.UUID) -> Optional[Client]:
        result = await self.db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Client]:
        result = await self.db.execute(
            select(Client).where(
                Client.slug == slug,
                Client.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


# ── User Repository ───────────────────────────────────────────────────────────

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        client_id: uuid.UUID,
        email: str,
        password_hash: str,
        full_name: str,
        role: str = "admin",
    ) -> User:
        user = User(
            client_id=client_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_client(
        self, email: str, client_id: uuid.UUID
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.client_id == client_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Used during login when client context isn't known yet."""
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.deleted_at.is_(None),
                User.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def update_login_success(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.now(timezone.utc),
                failed_login_attempts=0,
                locked_until=None,
            )
        )

    async def increment_failed_login(
        self, user_id: uuid.UUID, lock_until: Optional[datetime] = None
    ) -> None:
        values = {"failed_login_attempts": User.failed_login_attempts + 1}
        if lock_until:
            values["locked_until"] = lock_until
        await self.db.execute(
            update(User).where(User.id == user_id).values(**values)
        )


# ── Document Repository ───────────────────────────────────────────────────────

class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        client_id: uuid.UUID,
        uploaded_by_id: uuid.UUID,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> Document:
        doc = Document(
            client_id=client_id,
            uploaded_by_id=uploaded_by_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            status="pending",
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_by_id_and_client(
        self, document_id: uuid.UUID, client_id: uuid.UUID
    ) -> Optional[Document]:
        """Strict client scoping prevents cross-tenant access."""
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.client_id == client_id,  # CRITICAL: tenant isolation
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_client(
        self, client_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Document], int]:
        offset = (page - 1) * page_size

        # Get total count
        count_result = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.client_id == client_id,
                Document.deleted_at.is_(None),
            )
        )
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            select(Document)
            .where(
                Document.client_id == client_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        documents = result.scalars().all()
        return list(documents), total

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        values = {"status": status}
        if chunk_count is not None:
            values["chunk_count"] = chunk_count
        if error_message is not None:
            values["error_message"] = error_message
        await self.db.execute(
            update(Document).where(Document.id == document_id).values(**values)
        )

    async def soft_delete(self, document_id: uuid.UUID) -> None:
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(deleted_at=datetime.now(timezone.utc))
        )


# ── Query Repository ──────────────────────────────────────────────────────────

class QueryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
    ) -> Query:
        query = Query(
            client_id=client_id,
            user_id=user_id,
            question=question,
            status="processing",
        )
        self.db.add(query)
        await self.db.flush()
        return query

    async def complete(
        self,
        query_id: uuid.UUID,
        answer: str,
        source_documents: list,
        tokens_used: int,
        latency_ms: int,
    ) -> None:
        await self.db.execute(
            update(Query)
            .where(Query.id == query_id)
            .values(
                answer=answer,
                source_documents=source_documents,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                status="success",
            )
        )

    async def fail(self, query_id: uuid.UUID, error_message: str) -> None:
        await self.db.execute(
            update(Query)
            .where(Query.id == query_id)
            .values(status="failed", error_message=error_message)
        )

    async def list_by_client(
        self,
        client_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[Query], int]:
        conditions = [Query.client_id == client_id]
        if start_date:
            conditions.append(Query.created_at >= start_date)
        if end_date:
            conditions.append(Query.created_at <= end_date)

        offset = (page - 1) * page_size

        count_result = await self.db.execute(
            select(func.count(Query.id)).where(*conditions)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Query)
            .where(*conditions)
            .order_by(Query.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_all_for_export(
        self,
        client_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Query]:
        """Get all queries for export — no pagination, use carefully."""
        conditions = [Query.client_id == client_id]
        if start_date:
            conditions.append(Query.created_at >= start_date)
        if end_date:
            conditions.append(Query.created_at <= end_date)

        result = await self.db.execute(
            select(Query)
            .where(*conditions)
            .order_by(Query.created_at.asc())
        )
        return list(result.scalars().all())


# ── Audit Repository ──────────────────────────────────────────────────────────

class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        client_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> AuditLog:
        """
        Audit logs are append-only. Never update or delete.
        Fire-and-forget: caller shouldn't await this in the critical path.
        """
        entry = AuditLog(
            action=action,
            client_id=client_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            extra=extra,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
