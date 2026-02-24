"""
SQLAlchemy ORM models for all database tables.

Architecture Decisions:
- UUID primary keys: no sequential ID enumeration attacks, works across distributed systems
- soft_delete via deleted_at timestamp: preserve data for audit, allow recovery
- Proper indexes on foreign keys and frequently queried columns
- created_at/updated_at via server_default and onupdate for DB-level consistency
- All string columns have explicit max lengths (prevents unbounded data)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    """Reusable mixin: auto-populated created_at / updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Reusable mixin: soft delete via deleted_at timestamp."""
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,  # Common query pattern: WHERE deleted_at IS NULL
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ── Client (Tenant) ───────────────────────────────────────────────────────────

class Client(TimestampMixin, SoftDeleteMixin, Base):
    """
    Top-level tenant entity.
    Every piece of data is scoped to a client_id.
    Chroma collection name: f"client_{client.id}"
    """
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # Plan tier — used for rate limiting and feature gating
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="starter",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Arbitrary client-specific config (webhook URLs, branding, etc.)",
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="client")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="client")
    queries: Mapped[list["Query"]] = relationship("Query", back_populates="client")

    __table_args__ = (
        Index("ix_clients_slug", "slug"),
        Index("ix_clients_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.name}>"


# ── User ──────────────────────────────────────────────────────────────────────

class User(TimestampMixin, SoftDeleteMixin, Base):
    """
    Application user, always scoped to a client (tenant).
    A user can only access their own client's data.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="member",
        comment="admin | member | viewer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="users")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="uploaded_by")
    queries: Mapped[list["Query"]] = relationship("Query", back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        # Email unique per client — same email can register under different tenants
        UniqueConstraint("client_id", "email", name="uq_users_client_email"),
        Index("ix_users_email", "email"),
        Index("ix_users_client_id", "client_id"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


# ── Document ──────────────────────────────────────────────────────────────────

class Document(TimestampMixin, SoftDeleteMixin, Base):
    """
    Uploaded document metadata.
    Actual file stored on disk at: uploads/{client_id}/{stored_filename}
    Vector embeddings in ChromaDB collection: client_{client_id}
    """
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Nullable: user may be deleted but document stays
    )
    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original filename as provided by uploader",
    )
    stored_filename: Mapped[str] = mapped_column(
        String(600),
        nullable=False,
        comment="{uuid4}_{safe_filename} — prevents path traversal & duplicates",
    )
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Absolute path on server filesystem",
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="pending",
        comment="pending | processing | indexed | failed",
    )
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_metadata: Mapped[Optional[dict]] = mapped_column(
        "doc_metadata",
        JSONB,
        nullable=True,
        comment="Extracted metadata: page count, author, etc.",
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="documents")
    uploaded_by: Mapped[Optional["User"]] = relationship("User", back_populates="documents")

    __table_args__ = (
        Index("ix_documents_client_id", "client_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_client_status", "client_id", "status"),
    )


# ── Query ─────────────────────────────────────────────────────────────────────

class Query(TimestampMixin, Base):
    """
    Stores every RAG query and its response.
    Used for: analytics, billing, debugging, export.
    """
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_documents: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {doc_id, chunk_id, score} used in retrieval",
    )
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="success",
        comment="success | failed | filtered",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="queries")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="queries")

    __table_args__ = (
        Index("ix_queries_client_id", "client_id"),
        Index("ix_queries_user_id", "user_id"),
        Index("ix_queries_created_at", "created_at"),
        # For date-range exports
        Index("ix_queries_client_created", "client_id", "created_at"),
    )


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable audit trail. No update/delete permitted at application level.
    Captures security-relevant events for compliance.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="LOGIN | LOGOUT | UPLOAD | DELETE_DOC | QUERY | EXPORT",
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max len
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_client_id", "client_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
