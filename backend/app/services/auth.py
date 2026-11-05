from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import security
from app.config import settings
from app.errors import ApiError, unauthorized
from app.models import User
from app.repositories import users as users_repository


def _user_from_claims(claims: dict[str, Any]) -> User:
    email = claims["email"]
    return User(
        google_sub=claims["sub"],
        email=email,
        nume=(claims.get("family_name") or claims.get("name") or email.split("@")[0])[:100],
        prenume=(claims.get("given_name") or claims.get("name") or email.split("@")[0])[:100],
    )


def _ensure_allowed_domain(claims: dict[str, Any]) -> None:
    # `hd` este emis doar pentru conturile organizației; un cont Google obișnuit poate avea orice adresă de email.
    domain = settings.google_allowed_domain
    if claims.get("hd") != domain or not claims["email"].lower().endswith(f"@{domain}"):
        raise ApiError(403, "ACCES_INTERZIS", f"Conectează-te cu contul instituțional @{domain}.")


def login_with_google(db: Session, google_token: str) -> User:
    claims = security.verify_google_id_token(google_token)
    if not claims.get("email") or not claims.get("email_verified"):
        raise unauthorized("Contul Google nu are un email verificat.")
    _ensure_allowed_domain(claims)

    user = users_repository.get_by_google_sub(db, claims["sub"])
    if user is None:
        user = _user_from_claims(claims)
        db.add(user)
    else:
        # Numele rămâne cel din profil; emailul urmează contul Google, pentru notificări.
        user.email = claims["email"]

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        # Două prime autentificări simultane: cealaltă cerere a creat deja utilizatorul.
        user = users_repository.get_by_google_sub(db, claims["sub"])
        if user is None or user.email != claims["email"]:
            raise ApiError(409, "CONT_EXISTENT", "Emailul este deja asociat altui cont Google.") from error
    return user
