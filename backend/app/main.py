# AnCapTruyenLamVideo - FastAPI Main Application

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config import get_settings
from .database import Database
from .routes.story import router as story_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("AnCapTruyenLamVideo API Starting...")
    logger.info("=" * 60)

    try:
        await Database.connect()
        logger.info(f"Connection Type: {settings.connection_type}")
        logger.info(f"Database: {settings.database_name}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("The API will start but database operations will fail.")
        logger.error("Please check your MONGODB_URI configuration.")

    yield

    # Shutdown
    logger.info("AnCapTruyenLamVideo API Shutting down...")
    await Database.disconnect()


# Create FastAPI application
app = FastAPI(
    title="AnCapTruyenLamVideo API",
    description="""
    AnCapTruyenLamVideo API - Backend service for managing stories.

    ## Features
    - Full CRUD operations for Stories
    - MongoDB integration (supports both Atlas and local)
    - Async/await for optimal performance

    ## Stories
    Manage your stories with the following operations:
    - **GET /api/stories** - List all stories
    - **GET /api/stories/{id}** - Get a specific story
    - **POST /api/stories** - Create a new story
    - **PUT /api/stories/{id}** - Update an existing story
    - **DELETE /api/stories/{id}** - Delete a story
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Get settings
settings = get_settings()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(story_router)


@app.get("/", tags=["health"])
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "Welcome to AnCapTruyenLamVideo API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db = Database.get_database()
        await db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
        "connection_type": settings.connection_type
    }


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.environment == "development"
    )
