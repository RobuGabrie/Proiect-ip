from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rrm:rrm_dev@localhost:5432/rrm"
    cors_origins: str = "http://localhost:3000"
    google_client_id: str
    google_allowed_domain: str = "student.usv.ro"
    jwt_secret: str = Field(min_length=32)
    jwt_expires_seconds: int = 3600

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
