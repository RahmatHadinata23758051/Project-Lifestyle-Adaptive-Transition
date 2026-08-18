from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.core.config import settings

security = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    role: str = "authenticated"


def verify_supabase_jwt(token: str) -> AuthenticatedUser:
    """
    Verify Supabase JWT token and extract authenticated user context.
    Standardized to reject invalid, expired, or malformed tokens with 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Supabase JWT signature validation
        # Options allow validation of HS256 using JWT Secret, with audience verification bypassed if not configured
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256", "HS384", "HS512"],
            options={"verify_aud": False},
        )
        user_id: Optional[str] = payload.get("sub")
        email: Optional[str] = payload.get("email") or f"{user_id}@chronos.user"
        role: str = payload.get("role", "authenticated")

        if user_id is None:
            raise credentials_exception

        return AuthenticatedUser(id=str(user_id), email=str(email), role=role)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts and validates the authenticated user from the Bearer token.
    Never accepts user_id from query or body to determine ownership.
    """
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_supabase_jwt(auth_header.credentials)
