# AnCapTruyenLamVideo - AI Processor Service

import logging
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
        return f"""Bạn là một người kể chuyện chuyên nghiệp. Nhiệm vụ của bạn là đọc các hình ảnh manga và viết lại thành một câu chuyện văn xuôi hấp dẫn bằng tiếng Việt.

Manga: {manga_title}
{part_info}

Hãy xem các hình ảnh manga và viết thành một câu chuyện kể theo phong cách tiểu thuyết/truyện kể:

Yêu cầu:
- Viết như đang KỂ CHUYỆN cho người nghe, không phải hướng dẫn làm video
- Mô tả chi tiết bối cảnh, hành động, cảm xúc của nhân vật
- Chuyển tất cả đối thoại trong manga sang tiếng Việt tự nhiên
- Sử dụng văn phong hấp dẫn, lôi cuốn người đọc
- Kể chuyện mạch lạc, liền mạch từ đầu đến cuối
- Thêm các chi tiết miêu tả để người đọc/nghe có thể hình dung được câu chuyện

Viết theo phong cách: "Câu chuyện bắt đầu khi... Nhân vật chính... Anh ta nói:... Sau đó..."

---
CÂU CHUYỆN:
"""

    def _build_continuation_prompt(self, manga_title: str, part_info: str) -> str:
        """Build prompt for continuation parts."""
        return f"""Tiếp tục kể câu chuyện manga "{manga_title}".
{part_info}

Tiếp tục kể chuyện từ phần trước một cách mạch lạc. Nhớ giữ văn phong kể chuyện hấp dẫn:
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
                    "content": "Bạn là một người kể chuyện tài ba. Hãy kể lại nội dung manga thành câu chuyện văn xuôi hấp dẫn bằng tiếng Việt. Viết như đang kể chuyện cho người nghe, không phải hướng dẫn làm video."
                },
                {
                    "role": "user",
                    "content": content
                }
            ]

            try:
                script = await self._call_ai_api(messages)
                all_scripts.append(f"=== PHẦN {chunk_num}/{len(chunks)} ===\n\n{script}")
                logger.info(f"Chunk {chunk_num} generated {len(script)} characters")

                if progress_callback:
                    await progress_callback(chunk_num, len(chunks))

            except Exception as e:
                logger.error(f"AI processing error for chunk {chunk_num}: {e}")
                all_scripts.append(f"=== PHẦN {chunk_num}/{len(chunks)} ===\n\n[Lỗi xử lý: {str(e)}]")

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

    async def combine_scripts(self, task_id: str, manga_title: str) -> str:
        """
        Combine all batch scripts into a single final script.
        Returns path to combined file.
        """
        task_path = self.content_path / task_id

        if not task_path.exists():
            return ""

        # Get all batch script files
        script_files = sorted(task_path.glob("batch_*.txt"))

        if not script_files:
            return ""

        # Combine content
        combined_content = f"""================================================================================
CÂU CHUYỆN MANGA - BẢN ĐẦY ĐỦ
================================================================================
Manga: {manga_title}
Task ID: {task_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Batches: {len(script_files)}
================================================================================

"""
        for script_file in script_files:
            with open(script_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Skip the header from individual batch files
                if "================================================================================\n\n" in content:
                    content = content.split("================================================================================\n\n", 2)[-1]
                combined_content += content + "\n\n"

        # Save combined file
        combined_path = task_path / f"{manga_title.replace(' ', '_')}_full_script.txt"
        with open(combined_path, "w", encoding="utf-8") as f:
            f.write(combined_content)

        logger.info(f"Combined {len(script_files)} scripts into {combined_path}")
        return str(combined_path)


# Singleton instance
ai_processor = AIProcessor()
