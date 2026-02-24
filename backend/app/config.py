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

    # DeepInfra Configuration
    deepinfra_api_key: str = ""
    deepinfra_base_url: str = "https://api.deepinfra.com/v1/openai"
    qwen_model: str = "Qwen/Qwen3-VL-30B-A3B-Instruct"

    # Crawler Configuration
    crawler_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    crawler_delay_min: float = 1.0
    crawler_delay_max: float = 3.0
    crawler_timeout: int = 30
    crawler_max_retries: int = 3
    batch_size: int = 10  # Chapters per AI batch
    max_chapters_dev: int = 5  # Max chapters to process in development mode

    # Storage paths
    content_dir: str = "content"
    images_dir: str = "images"
    videos_dir: str = "videos"

    # Telegram Bot Configuration
    telegram_bot_token: str = ""
    telegram_enabled: bool = True

    # YouTube Upload Configuration
    youtube_client_secrets_file: str = "client_secrets.json"
    youtube_credentials_file: str = "youtube_credentials.json"
    youtube_enabled: bool = True
    youtube_default_privacy: str = "private"  # private, unlisted, public
    youtube_default_category: str = "22"  # 22 = People & Blogs

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
