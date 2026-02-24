# AnCapTruyenLamVideo - FastAPI Main Application

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config import get_settings
from .database import Database
from .routes.crawler import router as crawler_router
from .services.telegram_bot import telegram_bot

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

    # Start Telegram bot
    try:
        await telegram_bot.start()
        if settings.telegram_bot_token:
            logger.info("Telegram bot started")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")

    yield

    # Shutdown
    logger.info("AnCapTruyenLamVideo API Shutting down...")
    await telegram_bot.stop()
    await Database.disconnect()


# Create FastAPI application
app = FastAPI(
    title="AnCapTruyenLamVideo API",
    description="""
    AnCapTruyenLamVideo API - Manga Crawler and Video Script Generator.

    ## Features
    - Crawl manga chapters from truyenqqno.com
    - Download manga images automatically
    - Generate Vietnamese video scripts using AI (Qwen3-VL)
    - Real-time progress updates via SSE
    - MongoDB integration for task management

    ## Crawler
    - **POST /api/crawler/tasks** - Create and start a crawl task
    - **GET /api/crawler/tasks** - List all tasks
    - **GET /api/crawler/tasks/{id}** - Get task details
    - **GET /api/crawler/tasks/{id}/events** - SSE progress stream
    - **POST /api/crawler/tasks/{id}/cancel** - Cancel a running task
    - **GET /api/crawler/content/{id}** - Get generated scripts
    """,
    version="2.0.0",
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
app.include_router(crawler_router)


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
