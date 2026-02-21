# AnCapTruyenLamVideo - Database Connection

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

from .config import get_settings

logger = logging.getLogger(__name__)


class Database:
    """
    MongoDB database connection manager using Motor async driver.
    Supports both MongoDB Atlas and local MongoDB connections.
    """

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """
        Establish connection to MongoDB.
        Works with both MongoDB Atlas (mongodb+srv://) and local MongoDB (mongodb://).
        """
        settings = get_settings()

        try:
            logger.info(f"Connecting to {settings.connection_type}...")
            logger.info(f"Database name: {settings.database_name}")

            # Create the Motor client
            cls.client = AsyncIOMotorClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000
            )

            # Get the database
            cls.db = cls.client[settings.database_name]

            # Verify the connection by pinging the server
            await cls.client.admin.command("ping")

            logger.info(f"Successfully connected to {settings.connection_type}")
            logger.info(f"Database: {settings.database_name}")

            # Log additional info for debugging
            server_info = await cls.client.server_info()
            logger.info(f"MongoDB version: {server_info.get('version', 'unknown')}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            logger.error("Please check your MONGODB_URI in the .env file")

            if settings.is_atlas_connection:
                logger.error("For MongoDB Atlas connections, ensure:")
                logger.error("  1. Your IP address is whitelisted")
                logger.error("  2. Username and password are correct")
                logger.error("  3. The cluster URL is correct")
            else:
                logger.error("For local MongoDB, ensure:")
                logger.error("  1. MongoDB is running (mongod service)")
                logger.error("  2. The connection string is correct")

            raise

    @classmethod
    async def disconnect(cls) -> None:
        """Close the MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if cls.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.db

    @classmethod
    def get_collection(cls, collection_name: str):
        """Get a collection from the database."""
        return cls.get_database()[collection_name]


# Convenience function for dependency injection
async def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency to get database instance."""
    return Database.get_database()
