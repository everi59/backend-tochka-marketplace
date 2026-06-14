from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import b2b_router, b2c_router
from app.api.v1.moderation_service import router as moderation_router
from app.core.store import NeoMarketStore, ServiceError
from app.infrastructure.database.adapters.pg_connection import DatabaseConnection
from app.infrastructure.config.config import APP_CONFIG, DB_CONFIG

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, APP_CONFIG.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("=== APPLICATION STARTUP ===")
    logger.info(f"App: {APP_CONFIG.APP_NAME} v{APP_CONFIG.APP_VERSION}")

    # Initialize database
    logger.info("Creating DatabaseConnection...")
    db_connection = None
    try:
        db_connection = DatabaseConnection()
    except Exception as exc:
        logger.warning("Database startup skipped: %s", exc)

    # Проверка подключения (опционально)
    if db_connection is not None:
        if await db_connection.health_check():
            logger.info(f"Database connected: {DB_CONFIG.DB_HOST}:{DB_CONFIG.DB_PORT}")
        else:
            logger.error("Database connection failed!")

    app.state.db_connection = db_connection
    app.state.store = NeoMarketStore()

    # Create directories для статики
    _ensure_directories()

    logger.info("=== APPLICATION READY ===")

    yield

    # Shutdown
    logger.info("=== APPLICATION SHUTDOWN ===")
    if db_connection is not None:
        await db_connection.close()


def _ensure_directories():
    """Create necessary directories"""
    dirs = [APP_CONFIG.STATIC_DIR, APP_CONFIG.IMAGES_DIR]
    for dir_path in dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory created: {path}")


app = FastAPI(
    title=APP_CONFIG.APP_NAME,
    version=APP_CONFIG.APP_VERSION,
    description="Marketplace API",
    docs_url=APP_CONFIG.DOCS_URL if APP_CONFIG.DEBUG else None,
    redoc_url=APP_CONFIG.REDOC_URL if APP_CONFIG.DEBUG else None,
    openapi_url=APP_CONFIG.OPENAPI_URL if APP_CONFIG.DEBUG else None,
    lifespan=lifespan,
    debug=APP_CONFIG.DEBUG,
)


def _flat_error_message(detail: object, default: str) -> str:
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                location = ".".join(str(part) for part in item.get("loc", []) if part != "body")
                message = item.get("msg", default)
                parts.append(f"{location}: {message}" if location else str(message))
            else:
                parts.append(str(item))
        return "; ".join(parts) or default
    if isinstance(detail, dict):
        if "message" in detail:
            return str(detail["message"])
        return "; ".join(f"{key}: {value}" for key, value in detail.items()) or default
    if isinstance(detail, str):
        return detail
    return default


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": _flat_error_message(exc.errors(), "Validation error")},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"code", "message"}.issubset(exc.detail):
        payload = {"code": exc.detail["code"], "message": exc.detail["message"]}
    else:
        payload = {"code": "HTTP_ERROR", "message": _flat_error_message(exc.detail, "HTTP error")}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    payload = {"code": exc.code, "message": exc.message}
    if exc.details:
        payload["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=payload)

# Provide eager defaults for app state so imports and tests can access them
# even before the lifespan context is entered.
app.state.store = NeoMarketStore()
app.state.db_connection = None

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_CONFIG.get_cors_origins(),
    allow_credentials=APP_CONFIG.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(APP_CONFIG.STATIC_DIR)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=APP_CONFIG.STATIC_DIR), name="static")

# Include routers
app.include_router(b2c_router)
app.include_router(b2b_router)
app.include_router(moderation_router, prefix="/api/v1/moderation", tags=["Moderation"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    db_connection = getattr(app.state, "db_connection", None)
    db_status = await db_connection.health_check() if db_connection is not None else False
    return {
        "status": "ok" if db_status else "degraded",
        "version": APP_CONFIG.APP_VERSION,
        "database": "connected" if db_status else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=APP_CONFIG.HOST,
        port=APP_CONFIG.PORT,
        reload=APP_CONFIG.DEBUG,
    )
