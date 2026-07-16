import uuid

import jwt
import structlog
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.config import settings

log = structlog.get_logger()

_jwks_client = PyJWKClient(settings.supabase_jwks_url)


def verify_token(token: str) -> tuple[uuid.UUID, str]:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        log.warning("auth.token_verification_failed", reason="invalid_or_expired", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        log.warning("auth.token_verification_failed", reason="missing_claims")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        log.warning("auth.token_verification_failed", reason="malformed_subject", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    return user_id, email
