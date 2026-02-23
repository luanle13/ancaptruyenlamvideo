# AnCapTruyenLamVideo - AI Processor Service

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from openai import AsyncOpenAI

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIProcessor:
    """Processes manga images with Qwen3-VL via DeepInfra."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepinfra_api_key,
            base_url=settings.deepinfra_base_url,
        )
        self.content_path = Path(settings.content_dir)
        self.content_path.mkdir(parents=True, exist_ok=True)

    def _build_prompt(self, manga_title: str, part_info: str) -> str:
        """Build the Vietnamese story narration prompt."""
        return f"""Viết lại nội dung manga thành câu chuyện văn xuôi tiếng Việt.

Manga: {manga_title}

QUY TẮC BẮT BUỘC:
1. CHỈ viết nội dung câu chuyện, KHÔNG viết lời chào, lời giới thiệu, hay bình luận
2. KHÔNG lặp lại câu hoặc cụm từ
3. KHÔNG viết "Tôi sẽ...", "Hãy để tôi...", "Tất nhiên rồi...", hay bất kỳ câu trả lời nào
4. Bắt đầu viết câu chuyện NGAY LẬP TỨC
5. Mỗi hình ảnh = một đoạn văn mới
6. Dịch tất cả đối thoại sang tiếng Việt tự nhiên

BẮT ĐẦU VIẾT NGAY:
"""

    def _build_continuation_prompt(self, manga_title: str, part_info: str) -> str:
        """Build prompt for continuation parts."""
        return f"""Tiếp tục viết câu chuyện "{manga_title}".

QUY TẮC: KHÔNG lặp câu, KHÔNG viết lời chào/bình luận, CHỈ viết nội dung câu chuyện.

TIẾP TỤC:
"""

    async def _call_ai_api(self, messages: list) -> str:
        """Make a single API call to the AI model."""
        response = await self.client.chat.completions.create(
            model=settings.qwen_model,
            messages=messages,
            max_tokens=8000,
            temperature=0.7,
        )
        return response.choices[0].message.content

    async def process_batch(
        self,
        task_id: str,
        batch_number: int,
        chapter_images: Dict[str, List[dict]],
        manga_title: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Process a batch of chapter images with Qwen3-VL.
        Processes ALL images by splitting into chunks of 20 images per API call.
        chapter_images: {chapter_number: [{path, base64, media_type}, ...], ...}
        Returns Vietnamese script text.
        """
        IMAGES_PER_REQUEST = 20  # API limit is 30, use 20 for safety

        # Get chapter range
        chapters = sorted(chapter_images.keys(), key=lambda x: float(x) if x.replace(".", "").isdigit() else 0)
        if chapters:
            chapter_range = f"{chapters[0]} - {chapters[-1]}"
        else:
            chapter_range = f"Batch {batch_number}"

        # Flatten all images with chapter info
        all_images = []
        for chapter_num in chapters:
            for img in chapter_images[chapter_num]:
                all_images.append({
                    "chapter": chapter_num,
                    "image": img
                })

        total_images = len(all_images)
        logger.info(f"Processing AI batch {batch_number} for chapters {chapter_range} with {total_images} total images")

        if total_images == 0:
            return "Không có hình ảnh để xử lý."

        # Split into chunks of IMAGES_PER_REQUEST
        chunks = []
        for i in range(0, total_images, IMAGES_PER_REQUEST):
            chunks.append(all_images[i:i + IMAGES_PER_REQUEST])

        logger.info(f"Split into {len(chunks)} API calls of up to {IMAGES_PER_REQUEST} images each")

        # Process each chunk
        all_scripts = []

        for chunk_idx, chunk in enumerate(chunks):
            chunk_num = chunk_idx + 1
            logger.info(f"Processing chunk {chunk_num}/{len(chunks)} with {len(chunk)} images")

            # Build content for this chunk
            content = []

            # Add prompt
            part_info = f"Phần {chunk_num}/{len(chunks)} - Hình ảnh {chunk_idx * IMAGES_PER_REQUEST + 1} đến {chunk_idx * IMAGES_PER_REQUEST + len(chunk)}"

            if chunk_idx == 0:
                prompt = self._build_prompt(manga_title, part_info)
            else:
                prompt = self._build_continuation_prompt(manga_title, part_info)

            content.append({
                "type": "text",
                "text": prompt
            })

            # Track current chapter for headers
            current_chapter = None

            for item in chunk:
                # Add chapter header when chapter changes
                if item["chapter"] != current_chapter:
                    current_chapter = item["chapter"]
                    content.append({
                        "type": "text",
                        "text": f"\n--- CHƯƠNG {current_chapter} ---\n"
                    })

                # Add image
                img = item["image"]
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['media_type']};base64,{img['base64']}"
                    }
                })

            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": "Viết câu chuyện manga thành văn xuôi tiếng Việt. KHÔNG viết lời chào, bình luận, hay câu trả lời. KHÔNG lặp lại câu. CHỈ viết nội dung câu chuyện."
                },
                {
                    "role": "user",
                    "content": content
                }
            ]

            try:
                script = await self._call_ai_api(messages)
                all_scripts.append(script)
                logger.info(f"Chunk {chunk_num} generated {len(script)} characters")

                if progress_callback:
                    await progress_callback(chunk_num, len(chunks))

            except Exception as e:
                logger.error(f"AI processing error for chunk {chunk_num}: {e}")
                logger.warning(f"Skipping chunk {chunk_num} due to error")

        # Combine all scripts
        combined_script = "\n\n".join(all_scripts)
        logger.info(f"Generated combined script with {len(combined_script)} characters from {len(chunks)} chunks")

        return combined_script

    async def save_script(
        self,
        task_id: str,
        batch_number: int,
        script_content: str,
        chapter_range: str
    ) -> str:
        """
        Save script to content/{task_id}/batch_{n}_script.txt
        Returns file path.
        """
        task_path = self.content_path / task_id
        task_path.mkdir(parents=True, exist_ok=True)

        filename = f"batch_{batch_number:03d}_chapters_{chapter_range.replace(' ', '_').replace('-', 'to')}.txt"
        file_path = task_path / filename

        # Add header to script
        header = f"""================================================================================
CÂU CHUYỆN MANGA
================================================================================
Task ID: {task_id}
Batch: {batch_number}
Chapters: {chapter_range}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

"""
        full_content = header + script_content

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        logger.info(f"Saved script to {file_path}")
        return str(file_path)

    def _remove_duplicate_sentences(self, text: str) -> str:
        """Remove duplicate sentences from text, keeping first occurrence."""
        # Split into sentences (keeping punctuation)
        sentences = re.split(r'([.!?]+)', text)

        seen_sentences = set()
        cleaned_parts = []

        i = 0
        while i < len(sentences):
            sentence = sentences[i].strip()
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""

            if sentence:
                # Normalize for comparison (lowercase, remove extra spaces)
                normalized = re.sub(r'\s+', ' ', sentence.lower().strip())

                if normalized not in seen_sentences:
                    seen_sentences.add(normalized)
                    cleaned_parts.append(sentence + punct)

            i += 2 if punct else 1

        return " ".join(cleaned_parts)

    async def combine_scripts(self, task_id: str, manga_title: str) -> tuple[str, str]:
        """
        Combine all batch scripts into a single final script.
        Returns tuple of (path to combined file, raw script content for TTS).
        """
        task_path = self.content_path / task_id

        if not task_path.exists():
            return "", ""

        # Get all batch script files
        script_files = sorted(task_path.glob("batch_*.txt"))

        if not script_files:
            return "", ""

        # Combine raw content (for TTS - no metadata header)
        raw_content = ""
        for script_file in script_files:
            with open(script_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Skip the header from individual batch files
                if "================================================================================\n\n" in content:
                    content = content.split("================================================================================\n\n", 2)[-1]
                raw_content += content + "\n\n"

        # Remove duplicate sentences
        raw_content = self._remove_duplicate_sentences(raw_content)
        logger.info(f"Removed duplicate sentences, final length: {len(raw_content)} characters")

        # Create formatted content with metadata header (for human reading)
        header = f"""================================================================================
CÂU CHUYỆN MANGA - BẢN ĐẦY ĐỦ
================================================================================
Manga: {manga_title}
Task ID: {task_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Batches: {len(script_files)}
================================================================================

"""
        formatted_content = header + raw_content

        # Save combined file with header
        combined_path = task_path / f"{manga_title.replace(' ', '_')}_full_script.txt"
        with open(combined_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)

        logger.info(f"Combined {len(script_files)} scripts into {combined_path}")
        return str(combined_path), raw_content.strip()


# Singleton instance
ai_processor = AIProcessor()
