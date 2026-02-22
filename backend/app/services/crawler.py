# AnCapTruyenLamVideo - Main Crawler Service

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId

from ..database import Database
from ..config import get_settings
from ..models.crawler import (
    CrawlerTask,
    CrawlerTaskCreate,
    ChapterInfo,
    ProgressEvent,
    TaskStatus,
)
from ..utils.event_bus import event_bus
from .scraper import scraper
from .image_downloader import image_downloader
from .ai_processor import ai_processor

logger = logging.getLogger(__name__)
settings = get_settings()


class CrawlerService:
    """Main orchestrator for manga crawling."""

    COLLECTION_NAME = "crawler_tasks"
    _cancelled_tasks: set = set()

    @classmethod
    def _get_collection(cls):
        """Get the crawler tasks collection."""
        db = Database.get_database()
        return db[cls.COLLECTION_NAME]

    @classmethod
    def _serialize_task(cls, task: dict) -> dict:
        """Convert MongoDB document to API response format."""
        if task and "_id" in task:
            task["_id"] = str(task["_id"])
        return task

    @classmethod
    async def create_task(cls, task_data: CrawlerTaskCreate) -> dict:
        """Create a new crawl task."""
        collection = cls._get_collection()

        now = datetime.utcnow()
        task_doc = {
            "manga_url": task_data.manga_url,
            "manga_title": None,
            "status": TaskStatus.PENDING.value,
            "total_chapters": 0,
            "chapters_crawled": 0,
            "images_downloaded": 0,
            "total_images": 0,
            "batches_processed": 0,
            "total_batches": 0,
            "output_files": [],
            "error_message": None,
            "chapters": [],
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }

        result = await collection.insert_one(task_doc)
        task_doc["_id"] = result.inserted_id

        logger.info(f"Created crawl task {result.inserted_id} for {task_data.manga_url}")
        return cls._serialize_task(task_doc)

    @classmethod
    async def get_task(cls, task_id: str) -> Optional[dict]:
        """Get a task by ID."""
        collection = cls._get_collection()
        try:
            task = await collection.find_one({"_id": ObjectId(task_id)})
            return cls._serialize_task(task) if task else None
        except Exception:
            return None

    @classmethod
    async def get_all_tasks(cls) -> List[dict]:
        """Get all tasks, sorted by creation date."""
        collection = cls._get_collection()
        cursor = collection.find().sort("created_at", -1)
        tasks = await cursor.to_list(length=100)
        return [cls._serialize_task(task) for task in tasks]

    @classmethod
    async def update_task(cls, task_id: str, updates: dict):
        """Update a task."""
        collection = cls._get_collection()
        updates["updated_at"] = datetime.utcnow()
        await collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": updates}
        )

    @classmethod
    async def cancel_task(cls, task_id: str) -> bool:
        """Cancel a running task."""
        task = await cls.get_task(task_id)
        if not task:
            return False

        if task["status"] not in [TaskStatus.PENDING.value, TaskStatus.CRAWLING_CHAPTERS.value,
                                   TaskStatus.DOWNLOADING_IMAGES.value, TaskStatus.PROCESSING_AI.value]:
            return False

        cls._cancelled_tasks.add(task_id)
        await cls.update_task(task_id, {"status": TaskStatus.CANCELLED.value})
        await event_bus.publish(task_id, ProgressEvent(
            task_id=task_id,
            event_type="task_failed",
            message="Task cancelled by user",
            progress=0
        ))
        return True

    @classmethod
    def is_cancelled(cls, task_id: str) -> bool:
        """Check if a task is cancelled."""
        return task_id in cls._cancelled_tasks

    @classmethod
    async def _emit_progress(
        cls,
        task_id: str,
        event_type: str,
        message: str,
        progress: float,
        data: Optional[dict] = None
    ):
        """Emit a progress event."""
        event = ProgressEvent(
            task_id=task_id,
            event_type=event_type,
            message=message,
            progress=progress,
            data=data
        )
        await event_bus.publish(task_id, event)

    @classmethod
    async def start_crawl(cls, task_id: str):
        """
        Main crawling workflow:
        1. Parse manga page for chapters
        2. For each chapter, download images
        3. Every batch_size chapters (default 10), process with AI
        4. Save scripts to content/
        5. Emit progress events throughout

        In development mode, only processes max_chapters_dev chapters.
        """
        try:
            task = await cls.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            manga_url = task["manga_url"]

            # Emit task started
            await cls._emit_progress(task_id, "task_started", "Starting crawl...", 0)

            # Phase 1: Get manga info and chapter list
            await cls.update_task(task_id, {"status": TaskStatus.CRAWLING_CHAPTERS.value})
            await cls._emit_progress(task_id, "progress_update", "Fetching manga info...", 5)

            manga_info = await scraper.get_manga_info(manga_url)
            manga_title = manga_info["title"]
            chapters = manga_info["chapters"]

            # In development mode, limit to first N chapters for testing
            if settings.environment == "development":
                original_count = len(chapters)
                chapters = chapters[:settings.max_chapters_dev]
                logger.info(f"Development mode: limiting to {len(chapters)} of {original_count} chapters")

            total_chapters = len(chapters)
            total_batches = (total_chapters + settings.batch_size - 1) // settings.batch_size

            await cls.update_task(task_id, {
                "manga_title": manga_title,
                "total_chapters": total_chapters,
                "total_batches": total_batches,
                "chapters": [ChapterInfo(**ch, image_count=0).model_dump() for ch in chapters]
            })

            dev_note = " (dev mode)" if settings.environment == "development" else ""
            await cls._emit_progress(
                task_id,
                "chapters_found",
                f"Found {total_chapters} chapters for '{manga_title}'{dev_note}",
                10,
                {"total_chapters": total_chapters, "manga_title": manga_title}
            )

            if cls.is_cancelled(task_id):
                return

            # Phase 2: Download images chapter by chapter and process in batches
            await cls.update_task(task_id, {"status": TaskStatus.DOWNLOADING_IMAGES.value})

            batch_chapters: Dict[str, List[dict]] = {}
            current_batch = 1
            total_images_downloaded = 0
            output_files = []

            for i, chapter in enumerate(chapters):
                if cls.is_cancelled(task_id):
                    return

                chapter_num = chapter["chapter_number"]
                chapter_url = chapter["chapter_url"]

                # Get image URLs for this chapter
                await cls._emit_progress(
                    task_id,
                    "chapter_crawled",
                    f"Processing chapter {chapter_num}...",
                    10 + (i / total_chapters) * 40,
                    {"chapter": chapter_num, "chapters_crawled": i + 1}
                )

                image_urls = await scraper.get_chapter_images(chapter_url)

                if not image_urls:
                    logger.warning(f"No images found for chapter {chapter_num}")
                    continue

                # Download images
                async def image_progress(downloaded, total):
                    pass  # We'll batch update progress

                downloaded_paths = await image_downloader.download_chapter_images(
                    task_id,
                    chapter_num,
                    image_urls,
                    chapter_url,
                    image_progress
                )

                total_images_downloaded += len(downloaded_paths)

                await cls.update_task(task_id, {
                    "chapters_crawled": i + 1,
                    "images_downloaded": total_images_downloaded,
                    "total_images": total_images_downloaded  # Update as we go
                })

                await cls._emit_progress(
                    task_id,
                    "image_downloaded",
                    f"Downloaded {len(downloaded_paths)} images for chapter {chapter_num}",
                    10 + ((i + 1) / total_chapters) * 40,
                    {"chapter": chapter_num, "images": len(downloaded_paths), "total_downloaded": total_images_downloaded}
                )

                # Load images for AI processing
                chapter_images = await image_downloader.get_chapter_images_base64(task_id, chapter_num)
                batch_chapters[chapter_num] = chapter_images

                # Process batch every 50 chapters or at the end
                if len(batch_chapters) >= settings.batch_size or i == len(chapters) - 1:
                    if cls.is_cancelled(task_id):
                        return

                    await cls.update_task(task_id, {"status": TaskStatus.PROCESSING_AI.value})

                    chapter_range = f"{list(batch_chapters.keys())[0]}-{list(batch_chapters.keys())[-1]}"
                    await cls._emit_progress(
                        task_id,
                        "batch_processing",
                        f"Processing batch {current_batch}/{total_batches} (chapters {chapter_range})...",
                        50 + (current_batch / total_batches) * 40,
                        {"batch": current_batch, "chapter_range": chapter_range}
                    )

                    try:
                        # Process with AI
                        script = await ai_processor.process_batch(
                            task_id,
                            current_batch,
                            batch_chapters,
                            manga_title
                        )

                        # Save script
                        script_path = await ai_processor.save_script(
                            task_id,
                            current_batch,
                            script,
                            chapter_range
                        )
                        output_files.append(script_path)

                        await cls.update_task(task_id, {
                            "batches_processed": current_batch,
                            "output_files": output_files
                        })

                        await cls._emit_progress(
                            task_id,
                            "batch_completed",
                            f"Completed batch {current_batch}/{total_batches}",
                            50 + (current_batch / total_batches) * 40,
                            {"batch": current_batch, "script_path": script_path}
                        )

                    except Exception as e:
                        logger.error(f"AI processing error for batch {current_batch}: {e}")
                        # Continue with next batch even if one fails

                    # Clear batch for next round
                    batch_chapters = {}
                    current_batch += 1

                    # Go back to downloading status if more chapters remain
                    if i < len(chapters) - 1:
                        await cls.update_task(task_id, {"status": TaskStatus.DOWNLOADING_IMAGES.value})

            # Phase 3: Combine scripts and cleanup
            final_script = await ai_processor.combine_scripts(task_id, manga_title)
            if final_script:
                output_files.append(final_script)

            # Cleanup images
            await image_downloader.cleanup_task_images(task_id)

            # Mark as completed
            await cls.update_task(task_id, {
                "status": TaskStatus.COMPLETED.value,
                "output_files": output_files,
                "completed_at": datetime.utcnow()
            })

            await cls._emit_progress(
                task_id,
                "task_completed",
                f"Crawl completed! Generated {len(output_files)} script files.",
                100,
                {"output_files": output_files}
            )

            logger.info(f"Task {task_id} completed successfully")

        except asyncio.CancelledError:
            await cls.update_task(task_id, {"status": TaskStatus.CANCELLED.value})
            await cls._emit_progress(task_id, "task_failed", "Task cancelled", 0)

        except Exception as e:
            logger.error(f"Crawl error for task {task_id}: {e}")
            await cls.update_task(task_id, {
                "status": TaskStatus.FAILED.value,
                "error_message": str(e)
            })
            await cls._emit_progress(task_id, "task_failed", f"Error: {str(e)}", 0)

        finally:
            # Cleanup
            cls._cancelled_tasks.discard(task_id)
            await scraper.close()
            await image_downloader.close()
