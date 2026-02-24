"""
Authentication router: register, login, token refresh.
"""

import re
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, ConflictError, AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
    TokenData,
)
from app.core.config import settings
from app.models.models import User
from app.repositories.repositories import AuditRepository, ClientRepository, UserRepository
from app.schemas.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


def generate_slug(name: str) -> str:
    """Convert client name to URL-safe slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    # Append UUID fragment to ensure uniqueness
    slug = f"{slug[:50]}-{str(uuid.uuid4())[:8]}"
    return slug


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    summary="Register new user and create their tenant",
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new client (tenant) and admin user in one atomic transaction.
    First user of a client is always assigned the 'admin' role.
    """
    client_repo = ClientRepository(db)
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    # Check for existing email (global uniqueness for UX — same email per different client is allowed in DB)
    existing = await user_repo.get_by_email(body.email)
    if existing:
        raise ConflictError("An account with this email already exists")

    # Create client (tenant)
    slug = generate_slug(body.client_name)
    client = await client_repo.create(name=body.client_name, slug=slug)

    # Create admin user
    password_hash = hash_password(body.password)
    user = await user_repo.create(
        client_id=client.id,
        email=body.email,
        password_hash=password_hash,
        full_name=body.full_name,
        role="admin",
    )

    # Audit log
    await audit_repo.log(
        action="REGISTER",
        client_id=client.id,
        user_id=user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else None),
        request_id=getattr(request.state, "request_id", None),
    )

    # Generate tokens
    access_token = create_access_token(user.id, client.id, user.email)
    refresh_token = create_refresh_token(user.id, client.id)

    logger.info("User registered", user_id=str(user.id), client_id=str(client.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and get tokens",
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user with email/password.
    Implements account lockout after MAX_LOGIN_ATTEMPTS failed attempts.
    """
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")

    user = await user_repo.get_by_email(body.email)

    if not user:
        # Timing-safe: still compute hash to prevent email enumeration via timing
        hash_password("dummy_password_for_timing")
        raise AuthenticationError("Invalid email or password")

    # Check account lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        logger.warning("Locked account login attempt", user_id=str(user.id), ip=ip)
        raise AuthenticationError(
            f"Account locked. Try again after {user.locked_until.strftime('%H:%M UTC')}"
        )

    # Verify password
    if not verify_password(body.password, user.password_hash):
        # Increment failed attempts
        lock_until = None
        if user.failed_login_attempts + 1 >= settings.MAX_LOGIN_ATTEMPTS:
            from datetime import timedelta
            lock_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOCKOUT_DURATION_MINUTES
            )
            logger.warning("Account locked after failed attempts", user_id=str(user.id))

        await user_repo.increment_failed_login(user.id, lock_until)
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    # Success
    await user_repo.update_login_success(user.id)

    await audit_repo.log(
        action="LOGIN",
        client_id=user.client_id,
        user_id=user.id,
        ip_address=ip,
        request_id=getattr(request.state, "request_id", None),
    )

    access_token = create_access_token(user.id, user.client_id, user.email)
    refresh_token = create_refresh_token(user.id, user.client_id)

    logger.info("User logged in", user_id=str(user.id), client_id=str(user.client_id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    body: dict,  # Simple dict to avoid tight coupling
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token."""
    token = body.get("refresh_token")
    if not token:
        raise AuthenticationError("refresh_token is required")

    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid token type")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(payload["sub"]))

    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    access_token = create_access_token(user.id, user.client_id, user.email)
    new_refresh = create_refresh_token(user.id, user.client_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", summary="Get current user info")
async def get_me(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current authenticated user details."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.user_id)
    if not user:
        raise AuthenticationError("User not found")

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "client_id": str(user.client_id),
    }
