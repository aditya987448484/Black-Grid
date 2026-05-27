"""
Main FastAPI application with proper configuration and error handling
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import sys
from datetime import datetime

from app.core.config import get_settings
from app.api.api import api_router
from app.schemas.schemas import APIErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.debug,
)

# ============================================================================
# MIDDLEWARE SETUP
# ============================================================================

# Build a comprehensive CORS allow-list that covers every port Next.js
# might pick (3000–3005) so the browser never blocks a dev request even
# if the default port is already taken.
_cors = list(settings.backend_cors_origins)
for _port in [3000, 3001, 3002, 3003, 3004, 3005]:
    for _host in ["localhost", "127.0.0.1"]:
        _o = f"http://{_host}:{_port}"
        if _o not in _cors:
            _cors.append(_o)

# CORS Middleware - Allow frontend and other trusted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error": "Validation Error",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": "Internal Server Error",
            "details": str(exc) if settings.debug else "An error occurred",
        },
    )


# ============================================================================
# ROUTES
# ============================================================================

# Include API v1 routes
app.include_router(api_router, prefix=settings.api_v1_str)

# AI Analyst chat routes — router defines its own prefix (/api/ai-analyst)
from app.api.routes_ai_analyst import router as ai_analyst_router  # noqa: E402
app.include_router(ai_analyst_router)


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@app.get("/", tags=["info"])
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["info"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/status", tags=["info"])
async def status():
    """Detailed status endpoint"""
    return {
        "status": "operational",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "market_data_provider": settings.market_data_provider,
        "forecast_provider": settings.forecast_provider,
    }


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Market data provider: {settings.market_data_provider}")
    logger.info(f"CORS origins: {settings.backend_cors_origins}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info(f"Shutting down {settings.app_name}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

