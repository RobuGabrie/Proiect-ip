from fastapi import APIRouter

from app import security
from app.config import settings
from app.dependencies import DbSession
from app.schemas import AuthResponse, GoogleLoginRequest, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/google", operation_id="loginWithGoogle", response_model=AuthResponse)
def login_with_google(request: GoogleLoginRequest, db: DbSession) -> AuthResponse:
    user = auth_service.login_with_google(db, request.id_token)
    return AuthResponse(
        access_token=security.create_access_token(user.id),
        expires_in=settings.jwt_expires_seconds,
        user=UserOut.model_validate(user),
    )
