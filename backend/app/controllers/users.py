from fastapi import APIRouter

from app.dependencies import CurrentUser
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", operation_id="getCurrentUser", response_model=UserOut)
def get_current_user_profile(user: CurrentUser) -> CurrentUser:
    return user
