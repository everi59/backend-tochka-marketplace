from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.infrastructure.database.adapters.pg_connection import DatabaseConnection
from app.infrastructure.config.config import APP_CONFIG, DB_CONFIG
from app.api.v1.routers import api_v1_router
from app.utils.auth_middleware import AuthMiddleware

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
    db_connection = DatabaseConnection()

    # Проверка подключения (опционально)
    if await db_connection.health_check():
        logger.info(f"Database connected: {DB_CONFIG.DB_HOST}:{DB_CONFIG.DB_PORT}")
    else:
        logger.error("Database connection failed!")

    app.state.db_connection = db_connection
    app.state.sessions = {}

    # Create directories для статики
    # _ensure_directories()

    logger.info("=== APPLICATION READY ===")

    yield

    # Shutdown
    logger.info("=== APPLICATION SHUTDOWN ===")
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_CONFIG.get_cors_origins(),
    allow_credentials=APP_CONFIG.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    AuthMiddleware
)

# Static files
static_dir = Path(APP_CONFIG.STATIC_DIR)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=APP_CONFIG.STATIC_DIR), name="static")

# Include routers
app.include_router(api_v1_router, prefix=APP_CONFIG.API_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    db_status = await app.state.db_connection.health_check() if hasattr(app.state, 'db_connection') else False
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
