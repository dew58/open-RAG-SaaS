"""
JWT authentication and password hashing utilities.

Architecture Decision:
- bcrypt for password hashing (OWASP recommended, with cost factor)
- Short-lived access tokens (30min) + refresh tokens (7 days)
- Token payload includes client_id for tenant isolation enforcement
- python-jose for JWT (battle-tested, supports RS256 if needed later)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
import structlog
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

logger = structlog.get_logger(__name__)


# ── Password Hashing ──────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash password with bcrypt.
    rounds=12 takes ~300ms on modern hardware — strong enough to resist brute force.
    """
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time comparison prevents timing attacks.
    bcrypt.checkpw handles this internally.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ── JWT Tokens ────────────────────────────────────────────────────────────────

def create_access_token(
    user_id: UUID,
    client_id: UUID,
    email: str,
) -> str:
    """
    Create short-lived JWT access token.

    Payload includes:
    - sub: user identifier (standard JWT claim)
    - client_id: for tenant isolation in every downstream request
    - email: for audit logging without DB lookup
    - type: distinguish access vs refresh tokens
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "client_id": str(client_id),
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID, client_id: UUID) -> str:
    """Long-lived refresh token. Store hash in DB for revocation support."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "client_id": str(client_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.
    Raises AuthenticationError for any invalid token state.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed", error=str(e))
        raise AuthenticationError("Invalid or expired token")


# ── FastAPI Security Dependency ───────────────────────────────────────────────

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

http_bearer = HTTPBearer(auto_error=False)


class TokenData:
    """Parsed token payload, available via dependency injection."""
    def __init__(self, user_id: UUID, client_id: UUID, email: str):
        self.user_id = user_id
        self.client_id = client_id
        self.email = email


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> TokenData:
    """
    FastAPI dependency: validates Bearer token and returns user context.

    Used as:
        @router.get("/endpoint")
        async def handler(user: TokenData = Depends(get_current_user)):
            # user.client_id is the tenant isolator
    """
    if credentials is None:
        raise AuthenticationError("Authorization header missing")

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    try:
        return TokenData(
            user_id=UUID(payload["sub"]),
            client_id=UUID(payload["client_id"]),
            email=payload["email"],
        )
    except (KeyError, ValueError) as e:
        logger.error("Token payload malformed", error=str(e))
        raise AuthenticationError("Malformed token payload")
