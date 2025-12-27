"""
TAH (Tenant Access Hub) Authentication Module.

Implements JWT token validation, session management, and permission checking
following the TAH v2.0 integration specification.
"""
import hashlib
import logging
import secrets
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import List, Optional

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_session
from .models import User, UserSession

logger = logging.getLogger("dcp.auth")
settings = get_settings()

# Context variable for current org_id
current_org_id: ContextVar[Optional[str]] = ContextVar("current_org_id", default=None)
current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)

router = APIRouter(tags=["auth"])


@dataclass
class TAHTokenPayload:
    """Decoded TAH JWT token payload."""
    sub: str  # user_id (UUID)
    email: str
    name: Optional[str]
    tenant_id: str
    org_id: str  # Use this for filtering data
    roles: List[str]
    permissions: List[str]
    exp: int
    iat: int
    iss: str
    aud: str


class TAHTokenValidator:
    """Validates TAH JWT tokens using JWKS."""

    _instance: Optional["TAHTokenValidator"] = None

    def __init__(self, jwks_url: str, issuer: str, audience: str):
        self.jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        self.issuer = issuer
        self.audience = audience

    @classmethod
    def get_instance(cls) -> "TAHTokenValidator":
        """Get singleton instance of validator."""
        if cls._instance is None:
            cls._instance = cls(
                jwks_url=settings.tah_jwks_url,
                issuer=settings.tah_issuer,
                audience=settings.app_id,
            )
        return cls._instance

    def validate(self, token: str) -> TAHTokenPayload:
        """Validate JWT token and return payload."""
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]}
            )

            # Validate required fields
            if not payload.get("org_id"):
                raise ValueError("Missing org_id in token")

            return TAHTokenPayload(
                sub=payload["sub"],
                email=payload.get("email", ""),
                name=payload.get("name"),
                tenant_id=payload.get("tenant_id", ""),
                org_id=payload["org_id"],
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                exp=payload["exp"],
                iat=payload["iat"],
                iss=payload["iss"],
                aud=payload["aud"],
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidAudienceError:
            raise ValueError(f"Invalid audience. Expected: {self.audience}")
        except jwt.InvalidIssuerError:
            raise ValueError(f"Invalid issuer. Expected: {self.issuer}")
        except Exception as e:
            raise ValueError(f"Token validation failed: {e}")


class SessionInfo(BaseModel):
    """Current session information."""
    user_id: str
    org_id: str
    email: str
    name: Optional[str]
    roles: List[str]
    permissions: List[str]
    tenant_id: Optional[str]


async def get_current_session(
    request: Request,
    session_token: Optional[str] = Cookie(default=None, alias="session"),
    db: AsyncSession = Depends(get_session),
) -> UserSession:
    """Get current authenticated session from cookie."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_hash = hashlib.sha256(session_token.encode()).hexdigest()

    result = await db.execute(
        select(UserSession)
        .where(UserSession.token_hash == token_hash)
        .where(UserSession.expires_at > datetime.utcnow())
        .where(UserSession.revoked_at.is_(None))
    )
    user_session = result.scalar_one_or_none()

    if not user_session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Set context variables
    current_org_id.set(user_session.org_id)
    current_user_id.set(str(user_session.user_id))

    return user_session


async def get_optional_session(
    request: Request,
    session_token: Optional[str] = Cookie(default=None, alias="session"),
    db: AsyncSession = Depends(get_session),
) -> Optional[UserSession]:
    """Get current session if exists, None otherwise."""
    if not session_token:
        return None

    try:
        return await get_current_session(request, session_token, db)
    except HTTPException:
        return None


def get_org_id() -> str:
    """Get org_id from current context."""
    org_id = current_org_id.get()
    if not org_id:
        raise RuntimeError("org_id not set in context - ensure request is authenticated")
    return org_id


def has_permission(session: UserSession, required: str) -> bool:
    """Check if user has a specific permission."""
    permissions = session.tah_permissions or []
    if "*" in permissions:
        return True
    return required in permissions


def has_role(session: UserSession, required: str) -> bool:
    """Check if user has a specific role."""
    roles = session.tah_roles or []
    return required in roles


def require_permission(required: str):
    """Decorator to require permission for endpoint."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session = kwargs.get("user_session")
            if not session:
                raise HTTPException(status_code=401, detail="Not authenticated")
            if not has_permission(session, required):
                raise HTTPException(status_code=403, detail=f"Permission denied: {required}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


@router.get("/auth/tah-callback")
async def tah_callback(
    token: str = Query(..., description="TAH JWT token"),
    request: Request = None,
    db: AsyncSession = Depends(get_session),
):
    """
    TAH callback endpoint.

    Receives redirect from TAH App Launcher with JWT token.
    Validates token, creates/updates user, creates session, redirects to dashboard.
    """
    # 1. Validate token
    try:
        validator = TAHTokenValidator.get_instance()
        payload = validator.validate(token)
    except ValueError as e:
        logger.error(f"TAH token validation failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # 2. Get org_id directly from token (no local org table check)
    org_id = payload.org_id

    # 3. Upsert user (JIT provisioning)
    result = await db.execute(
        select(User).where(
            User.tah_user_id == payload.sub,
            User.org_id == org_id
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            tah_user_id=payload.sub,
            org_id=org_id,
            email=payload.email,
            name=payload.name,
        )
        db.add(user)
        logger.info(f"Created new user: {payload.email} for org: {org_id}")
    else:
        user.email = payload.email
        user.name = payload.name
        user.last_login_at = datetime.utcnow()
        logger.info(f"Updated user: {payload.email} for org: {org_id}")

    await db.flush()

    # 4. Create session
    session_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(session_token.encode()).hexdigest()

    user_session = UserSession(
        user_id=user.id,
        org_id=org_id,
        token_hash=token_hash,
        tah_permissions=payload.permissions,
        tah_roles=payload.roles,
        tenant_id=payload.tenant_id,
        tah_token_exp=datetime.fromtimestamp(payload.exp),
        expires_at=datetime.utcnow() + timedelta(hours=settings.session_expire_hours),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(user_session)
    await db.commit()

    # 5. Redirect with session cookie
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        "session",
        session_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.session_expire_hours * 3600,
    )

    logger.info(f"TAH login successful: {payload.email} ({org_id})")
    return response


@router.get("/auth/session", response_model=SessionInfo)
async def get_session_info(
    user_session: UserSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_session),
):
    """Get current session information."""
    result = await db.execute(
        select(User).where(User.id == user_session.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return SessionInfo(
        user_id=str(user.id),
        org_id=user_session.org_id,
        email=user.email,
        name=user.name,
        roles=user_session.tah_roles or [],
        permissions=user_session.tah_permissions or [],
        tenant_id=user_session.tenant_id,
    )


@router.post("/auth/logout")
async def logout(
    user_session: UserSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_session),
):
    """Logout and revoke session."""
    user_session.revoked_at = datetime.utcnow()
    await db.commit()

    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("session")

    return response


@router.get("/auth/check")
async def check_auth(
    user_session: Optional[UserSession] = Depends(get_optional_session),
):
    """Check if user is authenticated (public endpoint)."""
    if user_session:
        return {"authenticated": True, "org_id": user_session.org_id}
    return {"authenticated": False}
