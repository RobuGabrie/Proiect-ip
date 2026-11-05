from fastapi import APIRouter, status

from app.dependencies import AdminUser, CurrentUser, DbSession
from app.models import ResourceCategory
from app.schemas import CategoryInput, CategoryOut
from app.services import resources as service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", operation_id="listCategories", response_model=list[CategoryOut])
def list_categories(_: CurrentUser, db: DbSession) -> list[ResourceCategory]:
    return service.list_categories(db)


@router.post("", operation_id="createCategory", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryInput, _: AdminUser, db: DbSession) -> ResourceCategory:
    return service.create_category(db, data)


@router.put("/{category_id}", operation_id="updateCategory", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryInput, _: AdminUser, db: DbSession) -> ResourceCategory:
    return service.update_category(db, category_id, data)


@router.delete("/{category_id}", operation_id="deleteCategory", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, _: AdminUser, db: DbSession) -> None:
    service.delete_category(db, category_id)
