"""
FastAPI Main Application
========================

The entry point for the entire backend.
Defines all routes, middleware, and configurations.

Run with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

# Our imports
from app.config import settings
from app.database import check_database_connection
from app.routers import businesses, auth, predictions, customers, admin

# ===== LOGGING SETUP =====
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== CREATE FASTAPI APP =====
app = FastAPI(
    title=settings.app_name,
    description="Predict customer churn and track business actions & ROI",
    version="1.0.0",
    debug=settings.debug,
)

# ===== CORS MIDDLEWARE =====
# Allow frontend to call backend from different domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    """
    Runs when the server starts.
    Validates environment configuration and database connectivity.
    """
    logger.info("🚀 Starting Supermarket AI Backend...")
    
    try:
        settings.validate_for_startup()
        check_database_connection()
        logger.info("✅ Environment verified and database reachable")
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error during startup: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise


# ===== SHUTDOWN EVENT =====
@app.on_event("shutdown")
async def shutdown_event():
    """Runs when the server shuts down."""
    logger.info("🛑 Shutting down Supermarket AI Backend...")


# ===== HEALTH CHECK =====
@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    
    Use this to verify backend is running.
    
    Response: {"status": "healthy", "timestamp": "2024-05-01T10:30:00"}
    """
    check_database_connection()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat()
    }


# ===== REGISTER ROUTERS =====
# Include all route modules
app.include_router(businesses.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(customers.router, prefix='/api')
app.include_router(admin.router, prefix="/api")

logger.info("✅ All routers registered")


# ===== ROOT ENDPOINT =====
@app.get("/")
async def root():
    """
    Welcome endpoint.
    """
    return {
        "message": "Welcome to Customer Churn Intelligent Prediction System",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


# ===== ERROR HANDLERS =====
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Catch any unhandled exceptions and log them.
    """
    logger.exception("❌ Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "Unexpected server error"
        }
    )


if __name__ == "__main__":
    import uvicorn
    # Run with: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)