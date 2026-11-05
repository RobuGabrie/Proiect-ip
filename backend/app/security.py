from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.config import settings
from app.errors import ApiError, unauthorized

JWT_ALGORITHM = "HS256"


def verify_google_id_token(token: str) -> dict[str, Any]:
    try:
        return id_token.verify_oauth2_token(token, Request(), audience=settings.google_client_id)
    except TransportError as error:
        raise ApiError(503, "GOOGLE_INDISPONIBIL", "Autentificarea Google nu este disponibilă momentan.") from error
    except (ValueError, GoogleAuthError) as error:
        raise unauthorized("Token-ul Google nu este valid.") from error


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_expires_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def read_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError) as error:
        raise unauthorized() from error
