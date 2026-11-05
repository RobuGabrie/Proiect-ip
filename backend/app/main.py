from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.config import settings

API_PREFIX = "/api/v1"

app = FastAPI(
    title="Research Resource Manager API",
    version="1.0.0",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Verificare tehnică a mediului, în afara contractului din docs/api/openapi.yaml.
@app.get("/health", include_in_schema=False)
def health(response: Response) -> dict[str, str]:
    if database.database_is_available():
        return {"status": "ok", "database": "ok"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "database": "unavailable"}
