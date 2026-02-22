# AnCapTruyenLamVideo - Crawler Routes

import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from ..models.crawler import CrawlerTask, CrawlerTaskCreate, ProgressEvent
from ..services.crawler import CrawlerService
from ..utils.event_bus import event_bus
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/crawler", tags=["crawler"])


@router.post("/tasks", status_code=201, response_model=CrawlerTask)
async def create_crawl_task(
    task: CrawlerTaskCreate,
    background_tasks: BackgroundTasks
):
    """Create and start a new crawl task."""
    # Validate URL
    if "truyenqqno.com" not in task.manga_url and "truyenqq" not in task.manga_url:
        raise HTTPException(400, "URL must be from truyenqqno.com")

    created = await CrawlerService.create_task(task)
    background_tasks.add_task(CrawlerService.start_crawl, created["_id"])
    return created


@router.get("/tasks", response_model=List[CrawlerTask])
async def get_all_tasks():
    """Get all crawl tasks."""
    return await CrawlerService.get_all_tasks()


@router.get("/tasks/{task_id}", response_model=CrawlerTask)
async def get_task(task_id: str):
    """Get a specific task by ID."""
    task = await CrawlerService.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    success = await CrawlerService.cancel_task(task_id)
    if not success:
        raise HTTPException(400, "Cannot cancel task (not running or not found)")
    return {"message": "Task cancelled"}


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    """SSE endpoint for real-time task progress."""
    # Verify task exists
    task = await CrawlerService.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    async def event_generator():
        queue = await event_bus.subscribe(task_id)
        try:
            while True:
                try:
                    # Wait for event with timeout
                    event: ProgressEvent = await asyncio.wait_for(queue.get(), timeout=30)
                    yield {
                        "event": event.event_type,
                        "data": event.model_dump_json()
                    }
                    # End stream on completion or failure
                    if event.event_type in ["task_completed", "task_failed"]:
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "keepalive", "data": "{}"}
        finally:
            event_bus.unsubscribe(task_id, queue)

    return EventSourceResponse(event_generator())


@router.get("/content/{task_id}")
async def get_task_content(task_id: str):
    """Get list of generated script files for a task."""
    task = await CrawlerService.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    content_path = Path(settings.content_dir) / task_id
    if not content_path.exists():
        return {"files": []}

    files = [str(f.name) for f in content_path.iterdir() if f.is_file() and f.suffix == ".txt"]
    return {"files": sorted(files)}


@router.get("/content/{task_id}/{filename}")
async def download_script(task_id: str, filename: str):
    """Download a specific script file."""
    task = await CrawlerService.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    file_path = Path(settings.content_dir) / task_id / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "File not found")

    return FileResponse(
        file_path,
        media_type="text/plain; charset=utf-8",
        filename=filename
    )
