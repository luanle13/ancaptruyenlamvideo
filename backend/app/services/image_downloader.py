# AnCapTruyenLamVideo - Image Downloader Service

import asyncio
import base64
import logging
import os
import random
import shutil
from pathlib import Path
from typing import List, Callable, Optional

import aiohttp
import aiofiles

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ImageDownloader:
    """Downloads and stores manga images locally."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    def __init__(self):
        self.base_path = Path(settings.images_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=10, ssl=False)
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def _get_headers(self, referer: str) -> dict:
        """Get request headers."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Connection": "keep-alive",
        }

    def _get_chapter_path(self, task_id: str, chapter_number: str) -> Path:
        """Get path for chapter images."""
        # Sanitize chapter number for filesystem
        safe_chapter = chapter_number.replace(".", "_").replace("/", "_")
        path = self.base_path / task_id / safe_chapter
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def download_image(
        self,
        url: str,
        save_path: Path,
        referer: str,
        retry: int = 0
    ) -> bool:
        """Download a single image."""
        try:
            session = await self._get_session()
            headers = self._get_headers(referer)

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    async with aiofiles.open(save_path, "wb") as f:
                        await f.write(content)
                    return True
                elif response.status == 403 or response.status == 429:
                    if retry < 3:
                        await asyncio.sleep(5 * (retry + 1))
                        return await self.download_image(url, save_path, referer, retry + 1)
                    logger.error(f"Failed to download {url}: HTTP {response.status}")
                    return False
                else:
                    logger.error(f"Failed to download {url}: HTTP {response.status}")
                    return False
        except Exception as e:
            if retry < 3:
                await asyncio.sleep(3 * (retry + 1))
                return await self.download_image(url, save_path, referer, retry + 1)
            logger.error(f"Error downloading {url}: {e}")
            return False

    async def download_chapter_images(
        self,
        task_id: str,
        chapter_number: str,
        image_urls: List[str],
        referer: str,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """
        Download all images for a chapter.
        Returns list of local file paths.
        """
        chapter_path = self._get_chapter_path(task_id, chapter_number)
        downloaded_paths = []

        for i, url in enumerate(image_urls):
            # Determine file extension
            ext = ".jpg"
            if ".png" in url.lower():
                ext = ".png"
            elif ".webp" in url.lower():
                ext = ".webp"
            elif ".gif" in url.lower():
                ext = ".gif"

            filename = f"page_{i+1:04d}{ext}"
            save_path = chapter_path / filename

            # Add small delay between downloads
            if i > 0:
                await asyncio.sleep(random.uniform(0.3, 0.8))

            success = await self.download_image(url, save_path, referer)
            if success:
                downloaded_paths.append(str(save_path))
                if progress_callback:
                    await progress_callback(i + 1, len(image_urls))

        logger.info(f"Downloaded {len(downloaded_paths)}/{len(image_urls)} images for chapter {chapter_number}")
        return downloaded_paths

    async def get_chapter_images_base64(
        self,
        task_id: str,
        chapter_number: str
    ) -> List[dict]:
        """
        Load chapter images as base64 for AI processing.
        Returns list of {path, base64, media_type}.
        """
        chapter_path = self._get_chapter_path(task_id, chapter_number)
        images = []

        if not chapter_path.exists():
            return images

        # Get sorted list of image files
        image_files = sorted(
            [f for f in chapter_path.iterdir() if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif"]],
            key=lambda x: x.name
        )

        for img_path in image_files:
            try:
                async with aiofiles.open(img_path, "rb") as f:
                    content = await f.read()
                    b64 = base64.b64encode(content).decode("utf-8")

                    # Determine media type
                    ext = img_path.suffix.lower()
                    media_type = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".webp": "image/webp",
                        ".gif": "image/gif",
                    }.get(ext, "image/jpeg")

                    images.append({
                        "path": str(img_path),
                        "base64": b64,
                        "media_type": media_type,
                    })
            except Exception as e:
                logger.error(f"Error reading image {img_path}: {e}")

        return images

    async def cleanup_task_images(self, task_id: str):
        """Delete downloaded images after processing is complete."""
        task_path = self.base_path / task_id
        if task_path.exists():
            try:
                shutil.rmtree(task_path)
                logger.info(f"Cleaned up images for task {task_id}")
            except Exception as e:
                logger.error(f"Error cleaning up task {task_id}: {e}")

    def get_task_image_count(self, task_id: str) -> int:
        """Get total number of downloaded images for a task."""
        task_path = self.base_path / task_id
        if not task_path.exists():
            return 0

        count = 0
        for chapter_dir in task_path.iterdir():
            if chapter_dir.is_dir():
                count += len([f for f in chapter_dir.iterdir() if f.is_file()])
        return count


# Singleton instance
image_downloader = ImageDownloader()
