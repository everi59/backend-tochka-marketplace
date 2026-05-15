# Dependency utilities used across routers
from typing import List

from app.infrastructure.config.config import APP_CONFIG

# Synchronous helper for CORS origins

def get_cors_origins() -> List[str]:
    return APP_CONFIG.get_cors_origins()
