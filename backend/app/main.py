from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import database
from app.config import settings
from app.controllers import approvals, auth, categories, reservations, resources, users, waitlist
from app.errors import ApiError

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

for module in (auth, users, categories, resources, reservations, approvals, waitlist):
    app.include_router(module.router, prefix=API_PREFIX)


@app.exception_handler(ApiError)
def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"code": error.code, "message": error.message})


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    fields = ", ".join(str(item["loc"][-1]) for item in error.errors())
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": "DATE_INVALIDE", "message": f"Date invalide: {fields}."},
    )



# Verificare tehnică a mediului, în afara contractului din docs/api/openapi.yaml.
@app.get("/health", include_in_schema=False)
def health(response: Response) -> dict[str, str]:
    if database.database_is_available():
        return {"status": "ok", "database": "ok"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "database": "unavailable"}
