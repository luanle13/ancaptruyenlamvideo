# AnCapTruyenLamVideo - Crawler Models

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    CRAWLING_CHAPTERS = "crawling_chapters"
    DOWNLOADING_IMAGES = "downloading_images"
    PROCESSING_AI = "processing_ai"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChapterInfo(BaseModel):
    """Information about a single chapter."""
    chapter_number: str
    chapter_title: str
    chapter_url: str
    image_count: int = 0
    images_downloaded: bool = False
    ai_processed: bool = False


class CrawlerTaskCreate(BaseModel):
    """Model for creating a new crawler task."""
    manga_url: str = Field(..., description="URL of the manga on truyenqqno.com")


class CrawlerTask(BaseModel):
    """Model for crawler task response."""
    id: str = Field(..., alias="_id", description="Task ID")
    manga_url: str
    manga_title: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    total_chapters: int = 0
    chapters_crawled: int = 0
    images_downloaded: int = 0
    total_images: int = 0
    batches_processed: int = 0
    total_batches: int = 0
    output_files: List[str] = []
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class ProgressEvent(BaseModel):
    """Model for SSE progress events."""
    task_id: str
    event_type: Literal[
        "task_started",
        "chapters_found",
        "chapter_crawled",
        "image_downloaded",
        "batch_processing",
        "batch_completed",
        "task_completed",
        "task_failed",
        "progress_update"
    ]
    message: str
    progress: float = 0  # 0-100 percentage
    data: Optional[dict] = None
