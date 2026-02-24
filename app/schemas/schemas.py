"""
Pydantic v2 schemas for request validation and response serialization.

Architecture Decision:
- Separate Input/Output schemas prevent over-posting attacks
- Validators sanitize inputs before they reach the service layer
- Response schemas control exactly what data is returned to clients
- No SQLAlchemy models exposed directly (separation of concerns)
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ── Shared ────────────────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Any]


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    client_name: str = Field(min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("full_name", "client_name")
    @classmethod
    def sanitize_string(cls, v: str) -> str:
        # Strip control characters and excessive whitespace
        v = re.sub(r"[\x00-\x1f\x7f]", "", v).strip()
        if not v:
            raise ValueError("Field cannot be empty after sanitization")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Client ────────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    plan: str = Field(default="starter", pattern="^(starter|pro|enterprise)$")


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Document ──────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: str
    chunk_count: Optional[int]
    created_at: datetime
    uploaded_by_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DocumentResponse]


# ── Chat ──────────────────────────────────────────────────────────────────────

def sanitize_query(text: str) -> str:
    """
    Prompt injection mitigation:
    - Strip null bytes and control characters
    - Truncate to max length
    - Remove common injection patterns

    Note: This is defense-in-depth. The primary protection is the system prompt
    design and input/output framing in the RAG chain.
    """
    from app.core.config import settings

    # Remove null bytes and control characters (except newlines/tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Basic prompt injection patterns
    injection_patterns = [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"system\s*prompt\s*:",
        r"you\s+are\s+now\s+",
        r"act\s+as\s+(if\s+you\s+are|a\s+)",
        r"forget\s+(everything|all)\s+(you|above)",
        r"<\s*system\s*>",
        r"\[INST\]",
        r"###\s*Human:",
        r"###\s*Assistant:",
    ]

    text_lower = text.lower()
    for pattern in injection_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            raise ValueError("Query contains potentially harmful content")

    # Truncate
    return text[:settings.MAX_QUERY_LENGTH].strip()


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        return sanitize_query(v)

    @model_validator(mode="before")
    @classmethod
    def accept_query_alias(cls, data: Any) -> Any:
        """Accept 'query' as alias for 'question' for API compatibility."""
        if isinstance(data, dict) and "query" in data and "question" not in data:
            data = {**data, "question": data["query"]}
        return data


class SourceDocument(BaseModel):
    document_id: Optional[str]
    filename: Optional[str]
    page: Optional[int]
    score: Optional[float]
    excerpt: str = Field(max_length=500)


class ChatQueryResponse(BaseModel):
    query_id: uuid.UUID
    question: str
    answer: str
    sources: List[SourceDocument]
    tokens_used: Optional[int]
    latency_ms: int


# ── Query History ─────────────────────────────────────────────────────────────

class QueryHistoryItem(BaseModel):
    id: uuid.UUID
    question: str
    answer: Optional[str]
    status: str
    tokens_used: Optional[int]
    latency_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── User ──────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
