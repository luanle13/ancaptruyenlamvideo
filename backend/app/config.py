# AnCapTruyenLamVideo - Configuration Settings

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # MongoDB Configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "ancaptruyenlamvideo_db"

    # Server Configuration
    backend_port: int = 8000
    backend_host: str = "0.0.0.0"

    # CORS Configuration
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"

    # Environment
    environment: str = "development"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_atlas_connection(self) -> bool:
        """Check if using MongoDB Atlas (mongodb+srv://)."""
        return self.mongodb_uri.startswith("mongodb+srv://")

    @property
    def connection_type(self) -> str:
        """Return human-readable connection type."""
        if self.is_atlas_connection:
            return "MongoDB Atlas (Cloud)"
        return "Local MongoDB"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
