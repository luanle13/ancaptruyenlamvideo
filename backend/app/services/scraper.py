# AnCapTruyenLamVideo - Web Scraper Service

import asyncio
import random
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MangaScraper:
    """Scrapes manga data from truyenqqno.com"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=5, ssl=False)
            timeout = aiohttp.ClientTimeout(total=settings.crawler_timeout)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def _get_headers(self, referer: str = "https://truyenqqno.com/") -> Dict[str, str]:
        """Get request headers with random user agent."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": referer,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def _make_request(self, url: str, retry: int = 0) -> str:
        """Make HTTP request with retry logic and anti-scraping measures."""
        # Add delay between requests
        delay = random.uniform(settings.crawler_delay_min, settings.crawler_delay_max)
        await asyncio.sleep(delay)

        session = await self._get_session()
        headers = self._get_headers()

        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:  # Rate limited
                    if retry < settings.crawler_max_retries:
                        wait_time = 10 * (retry + 1)
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        return await self._make_request(url, retry + 1)
                elif response.status == 403:
                    logger.error(f"Access forbidden for {url}")
                    raise Exception(f"Access forbidden (403) for URL: {url}")
                else:
                    raise Exception(f"HTTP {response.status} for URL: {url}")
        except aiohttp.ClientError as e:
            if retry < settings.crawler_max_retries:
                wait_time = 5 * (retry + 1)
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(url, retry + 1)
            raise

    async def get_manga_info(self, url: str) -> Dict:
        """
        Parse main manga page for title and chapter list.
        Returns: {title: str, chapters: [{number, title, url}, ...]}
        """
        logger.info(f"Fetching manga info from: {url}")
        html = await self._make_request(url)
        soup = BeautifulSoup(html, "lxml")

        # Extract manga title
        title_elem = soup.select_one("h1.ttl-name, h1.story-name, .book-title h1, h1")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Manga"

        # Extract chapters - truyenqqno.com typically has chapter list in a div
        chapters = []

        # Try different selectors for chapter list
        chapter_selectors = [
            "div.list-chapter a",
            "div.works-chapter-list a",
            "ul.list-chapter a",
            ".chapter-list a",
            "#list-chapter a",
            ".list_chapter a",
        ]

        chapter_links = []
        for selector in chapter_selectors:
            chapter_links = soup.select(selector)
            if chapter_links:
                logger.info(f"Found chapters using selector: {selector}")
                break

        if not chapter_links:
            # Fallback: find all links that look like chapter links
            all_links = soup.find_all("a", href=True)
            chapter_links = [
                link for link in all_links
                if "chap" in link.get("href", "").lower()
            ]

        for link in chapter_links:
            href = link.get("href", "")
            if not href:
                continue

            # Make absolute URL
            chapter_url = urljoin(url, href)

            # Extract chapter number from URL or text
            chapter_text = link.get_text(strip=True)

            # Try to extract chapter number
            import re
            match = re.search(r"chap[^\d]*(\d+(?:\.\d+)?)", href.lower())
            if match:
                chapter_number = match.group(1)
            else:
                match = re.search(r"(\d+(?:\.\d+)?)", chapter_text)
                chapter_number = match.group(1) if match else str(len(chapters) + 1)

            chapters.append({
                "chapter_number": chapter_number,
                "chapter_title": chapter_text or f"Chapter {chapter_number}",
                "chapter_url": chapter_url,
            })

        # Sort chapters by number
        def sort_key(ch):
            try:
                return float(ch["chapter_number"])
            except ValueError:
                return 0

        chapters.sort(key=sort_key)

        logger.info(f"Found {len(chapters)} chapters for '{title}'")

        return {
            "title": title,
            "chapters": chapters,
        }

    async def get_chapter_images(self, chapter_url: str) -> List[str]:
        """
        Parse chapter page for image URLs.
        Returns list of image URLs.
        """
        logger.info(f"Fetching images from: {chapter_url}")
        html = await self._make_request(chapter_url)
        soup = BeautifulSoup(html, "lxml")

        image_urls = []

        # Try different selectors for manga images
        image_selectors = [
            "div.chapter-content img",
            "div.page-chapter img",
            "div.reading-content img",
            ".chapter-detail img",
            "#content-chapter img",
            ".content-chapter img",
            ".chapter_content img",
        ]

        images = []
        for selector in image_selectors:
            images = soup.select(selector)
            if images:
                logger.info(f"Found images using selector: {selector}")
                break

        if not images:
            # Fallback: find all images that look like manga pages
            all_images = soup.find_all("img")
            images = [
                img for img in all_images
                if any(x in str(img.get("src", "")).lower() or str(img.get("data-src", "")).lower()
                       for x in ["chapter", "page", "manga", "comic", "img"])
            ]

        for img in images:
            # Try different attributes for image URL
            src = img.get("data-src") or img.get("data-original") or img.get("src") or ""

            if src and not src.startswith("data:"):
                # Make absolute URL
                absolute_url = urljoin(chapter_url, src)
                image_urls.append(absolute_url)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in image_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} images in chapter")
        return unique_urls


# Singleton instance
scraper = MangaScraper()
