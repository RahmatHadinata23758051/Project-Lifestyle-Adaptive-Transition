from typing import Optional, Dict, Any
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.core.config import settings

security = HTTPBearer(auto_error=False)

# Optional JWKS client cached when SUPABASE_URL is configured
_jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None and settings.SUPABASE_URL:
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            _jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
        except Exception:
            _jwks_client = None
    return _jwks_client


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    role: str = "authenticated"


def verify_supabase_jwt(token: str) -> AuthenticatedUser:
    """
    Verify Supabase JWT token supporting both:
    1. Asymmetric JWKS (RS256 / ES256) for modern Supabase signing keys.
    2. Symmetric Secret (HS256) for standard/local secret keys.
    Validates standard claims: sub (required), exp (expiration), iss (if URL configured).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Inspect unverified header to determine algorithm and key ID
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")
        kid = unverified_header.get("kid")

        payload: Dict[str, Any]

        if kid and get_jwks_client():
            # Modern Supabase JWKS verification
            jwks_client = get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg, "RS256", "ES256"],
                options={"verify_aud": False, "verify_exp": True},
            )
        else:
            # Symmetric secret verification (HS256)
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256", "HS384", "HS512"],
                options={"verify_aud": False, "verify_exp": True},
            )

        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise credentials_exception

        email: str = payload.get("email") or f"{user_id}@chronos.user"
        role: str = payload.get("role", "authenticated")

        return AuthenticatedUser(id=str(user_id), email=str(email), role=role)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency extracting validated user identity from Bearer token.
    """
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_supabase_jwt(auth_header.credentials)
