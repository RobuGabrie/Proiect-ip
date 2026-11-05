from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import security
from app.database import get_db
from app.errors import forbidden, unauthorized
from app.models import Role, User
from app.repositories import users as users_repository

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise unauthorized()
    user = users_repository.get_by_id(db, security.read_user_id(credentials.credentials))
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role is not Role.ADMIN:
        raise forbidden("Doar administratorii pot face această operație.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
PageNumber = Annotated[int, Query(ge=1, alias="page")]
PageSize = Annotated[int, Query(ge=1, le=100, alias="pageSize")]
