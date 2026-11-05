from fastapi import APIRouter

from app.dependencies import AdminUser, CurrentUser, DbSession, PageNumber, PageSize
from app.errors import conflict, not_found
from app.models import Role, User
from app.repositories import users as users_repository
from app.schemas import UserOut, UserPage, UserProfileUpdate, UserRoleUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", operation_id="getCurrentUser", response_model=UserOut)
def get_current_user_profile(user: CurrentUser) -> User:
    return user


@router.patch("/me", operation_id="updateCurrentUser", response_model=UserOut)
def update_current_user(data: UserProfileUpdate, user: CurrentUser, db: DbSession) -> User:
    if data.nume is not None:
        user.nume = data.nume
    if data.prenume is not None:
        user.prenume = data.prenume
    db.commit()
    return user


@router.get("", operation_id="listUsers", response_model=UserPage)
def list_users(
    _: AdminUser,
    db: DbSession,
    q: str | None = None,
    role: Role | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> UserPage:
    items, total = users_repository.search(db, q, role, page, page_size)
    return UserPage(items=items, page=page, page_size=page_size, total=total)


@router.put("/{user_id}/role", operation_id="updateUserRole", response_model=UserOut)
def update_user_role(user_id: int, data: UserRoleUpdate, _: AdminUser, db: DbSession) -> User:
    target = users_repository.get_by_id(db, user_id)
    if target is None:
        raise not_found("Utilizatorul nu există.")
    if data.role is not Role.ADMIN and target.administered_resources:
        raise conflict("ADMIN_CU_RESURSE", "Utilizatorul administrează resurse. Înlocuiește-l mai întâi la acestea.")
    target.role = data.role
    db.commit()
    return target
