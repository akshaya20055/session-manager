from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import Base, engine
from app.exceptions.custom_exceptions import ConflictError, NotFoundError, ValidationError
from app.routers.sessions import router as sessions_router
from app.schemas.session_schema import ErrorResponse, HealthResponse
from app.utils.logger import configure_logging, logger


def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
        },
    )


def validation_error_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid request"

    error = errors[0]
    location = error.get("loc", ())
    field = str(location[-1]) if location else "field"
    error_type = str(error.get("type", ""))

    if error_type == "missing":
        return f"Missing required field: {field}"
    if "uuid" in error_type:
        return f"Invalid UUID: {field}"
    if "enum" in error_type:
        return f"Invalid status: {field}"

    message = str(error.get("msg", "Invalid request"))
    if message.startswith("Value error, "):
        return message.replace("Value error, ", "", 1)
    return message


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Session Manager API for controlling interview session lifecycles. "
            "The API supports starting, updating, pausing, resuming, ending, and "
            "querying interview sessions with consistent JSON error responses."
        ),
        version=settings.app_version,
        debug=settings.debug,
        openapi_tags=[
            {
                "name": "Health",
                "description": "Operational endpoints for service health checks.",
            },
            {
                "name": "Sessions",
                "description": (
                    "Interview session lifecycle operations. These endpoints enforce "
                    "status transitions and prevent duplicate ACTIVE sessions."
                ),
            },
        ],
    )

    if settings.create_tables_on_startup:
        Base.metadata.create_all(bind=engine)

    @app.exception_handler(NotFoundError)
    async def not_found_exception_handler(
        request: Request, exc: NotFoundError
    ) -> JSONResponse:
        logger.warning(
            "Validation Error: resource not found method=%s path=%s message=%s",
            request.method,
            request.url.path,
            exc.message,
        )
        return error_response(status.HTTP_404_NOT_FOUND, exc.message)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.warning(
            "Validation Error: method=%s path=%s message=%s",
            request.method,
            request.url.path,
            exc.message,
        )
        return error_response(status.HTTP_400_BAD_REQUEST, exc.message)

    @app.exception_handler(ConflictError)
    async def conflict_exception_handler(
        request: Request, exc: ConflictError
    ) -> JSONResponse:
        logger.warning(
            "Validation Error: conflict method=%s path=%s message=%s",
            request.method,
            request.url.path,
            exc.message,
        )
        return error_response(status.HTTP_409_CONFLICT, exc.message)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        message = validation_error_message(exc)
        logger.warning(
            "Validation Error: request validation failed method=%s path=%s message=%s",
            request.method,
            request.url.path,
            message,
        )
        return error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, message)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning(
            "HTTP Error: method=%s path=%s status_code=%s detail=%s",
            request.method,
            request.url.path,
            exc.status_code,
            exc.detail,
        )
        return error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception("Database Error: method=%s path=%s", request.method, request.url.path)
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Database error",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error: %s %s", request.method, request.url.path)
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
        )

    @app.get(
        "/health",
        tags=["Health"],
        response_model=HealthResponse,
        summary="Health Check",
        description="Returns a simple readiness signal for the API process.",
        response_description="Current API health state.",
        responses={
            200: {"description": "API is healthy."},
            500: {
                "model": ErrorResponse,
                "description": "Unexpected server error.",
            },
        },
    )
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    app.include_router(sessions_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
