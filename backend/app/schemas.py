from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.models import Role


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class GoogleLoginRequest(ApiModel):
    id_token: str = Field(min_length=1)


class UserOut(ApiModel):
    id: int
    email: str
    nume: str
    prenume: str
    role: Role


class AuthResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
