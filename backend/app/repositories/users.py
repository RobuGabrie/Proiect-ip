from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Role, User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_google_sub(db: Session, google_sub: str) -> User | None:
    return db.scalar(select(User).where(User.google_sub == google_sub))


def search(db: Session, q: str | None, role: Role | None, page: int, page_size: int) -> tuple[list[User], int]:
    query = select(User)
    if q:
        pattern = f"%{q}%"
        query = query.where(or_(User.nume.ilike(pattern), User.prenume.ilike(pattern), User.email.ilike(pattern)))
    if role:
        query = query.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(User.nume, User.prenume).offset((page - 1) * page_size).limit(page_size)).all()
    return list(items), total
