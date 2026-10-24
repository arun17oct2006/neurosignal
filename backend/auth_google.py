"""
auth_google.py — Google Sign-In (ID token) authentication for NeuroSignal AI.

Flow:
  1. Frontend loads Google Identity Services (GSI) and obtains a credential (ID token).
  2. Frontend POSTs that token to  POST /auth/google  on this backend.
  3. Backend verifies the token's signature, audience, and expiry via Google's public keys.
  4. Backend returns a signed JWT the frontend stores in memory / sessionStorage.
  5. All subsequent API calls carry  Authorization: Bearer <jwt>  and are validated by
     the  get_current_user  dependency — no password is ever stored or checked.

Requirements (add to requirements.txt):
    google-auth>=2.29
    python-jose[cryptography]>=3.3
    httpx>=0.27          # only needed if you add token refresh helpers
"""

from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

import os
import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration  (set these as environment variables — never hard-code)
# ---------------------------------------------------------------------------

# Your Google OAuth 2.0 client ID (from https://console.cloud.google.com)
GOOGLE_CLIENT_ID: str = os.environ["GOOGLE_CLIENT_ID"]

# Secret used to sign the JWT we issue.  Generate once with:
#   python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET: str = os.environ["JWT_SECRET"]

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 60 * 60 * 8  # 8 hours


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class GoogleAuthIn(BaseModel):
    """Body of  POST /auth/google."""
    credential: str          # The raw Google ID token string from GSI


class UserProfile(BaseModel):
    """Minimal profile extracted from a verified Google token.
    Nothing here is stored — it is derived fresh from Google on every login.
    """
    sub: str                 # Google's stable user ID (use this as your user key)
    email: str
    name: str
    picture: str             # Avatar URL hosted by Google
    email_verified: bool


class AuthResponse(BaseModel):
    """Returned to the frontend after successful authentication."""
    access_token: str        # Signed JWT — store in memory or sessionStorage
    token_type: str = "bearer"
    profile: UserProfile


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _verify_google_token(credential: str) -> dict:
    """
    Verify the Google ID token and return its decoded claims.

    Raises HTTPException(401) if the token is invalid, expired, or issued
    for a different client ID.
    """
    try:
        claims: dict = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,   # tolerate minor clock drift
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {exc}",
        ) from exc

    # Extra guard: verify the token was intended for THIS app.
    if claims.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token audience mismatch.",
        )

    return claims


def _issue_jwt(profile: UserProfile) -> str:
    """
    Create and sign a short-lived JWT encoding the user's identity.
    The JWT is verified on every protected request; no session state is kept
    server-side.
    """
    now = int(time.time())
    payload = {
        "sub": profile.sub,
        "email": profile.email,
        "name": profile.name,
        "picture": profile.picture,
        "iat": now,
        "exp": now + JWT_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_jwt(token: str) -> dict:
    """
    Decode and validate our own JWT.
    Raises HTTPException(401) on any failure.
    """
    try:
        payload: dict = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return payload


# ---------------------------------------------------------------------------
# FastAPI dependency — protect any route with:
#   current_user: CurrentUser = Depends(get_current_user)
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=True)
_optional_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> UserProfile:
    """
    FastAPI dependency that validates the JWT in the Authorization header
    and returns the decoded UserProfile.

    Usage:
        @app.get("/protected")
        def protected(user: UserProfile = Depends(get_current_user)):
            return {"hello": user.email}
    """
    payload = _decode_jwt(credentials.credentials)
    return UserProfile(
        sub=payload["sub"],
        email=payload["email"],
        name=payload["name"],
        picture=payload["picture"],
        email_verified=True,
    )


def get_optional_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_optional_bearer)
    ],
) -> UserProfile | None:
    if credentials is None:
        return None
    return get_current_user(credentials)


# Convenience type alias for route signatures
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]
OptionalCurrentUser = Annotated[UserProfile | None, Depends(get_optional_current_user)]


# ---------------------------------------------------------------------------
# Route handler — register this in main.py (see instructions in README)
# ---------------------------------------------------------------------------

async def google_login(body: GoogleAuthIn) -> AuthResponse:
    """
    POST /auth/google

    Accepts a Google ID token, verifies it, and returns a signed JWT.
    No user data is written to any database.
    """
    claims = _verify_google_token(body.credential)

    profile = UserProfile(
        sub=claims["sub"],
        email=claims["email"],
        name=claims.get("name", ""),
        picture=claims.get("picture", ""),
        email_verified=bool(claims.get("email_verified", False)),
    )

    token = _issue_jwt(profile)
    return AuthResponse(access_token=token, profile=profile)


async def logout() -> dict:
    """
    POST /auth/logout

    JWTs are stateless — 'logout' is handled client-side by discarding the
    token.  This endpoint exists so the frontend has a consistent hook for
    any future server-side cleanup (e.g. token revocation list).
    """
    return {"ok": True, "message": "Token discarded client-side."}
