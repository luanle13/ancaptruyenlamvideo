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

    STORY_STATE_PROMPT = """Tóm tắt TRẠNG THÁI TRUYỆN từ đoạn văn sau. Format ngắn gọn:

1. BỐI CẢNH: [Địa điểm và thời gian hiện tại - 1 câu]
2. NHÂN VẬT CÓ MẶT: [Liệt kê tên nhân vật đang trong cảnh]
3. VỪA XẢY RA: [2-3 sự kiện chính vừa diễn ra]
4. KHÔNG KHÍ: [Căng thẳng/Vui vẻ/Buồn/Hồi hộp/etc.]
5. ĐANG DIỄN RA: [Xung đột hoặc tình huống chưa giải quyết]

CHỈ TRẢ VỀ TÓM TẮT, KHÔNG VIẾT GÌ KHÁC."""

    SYSTEM_PROMPT = """Bạn là người kể chuyện manga chuyên nghiệp. Nhiệm vụ: chuyển thể manga thành văn xuôi tiếng Việt hấp dẫn.

NGUYÊN TẮC KỂ CHUYỆN:
1. BỐI CẢNH: Mô tả môi trường, địa điểm, thời gian rõ ràng khi chuyển cảnh.
2. HÀNH ĐỘNG: Kể chi tiết từng hành động, biểu cảm khuôn mặt, cử chỉ tay chân của nhân vật.
3. ĐỐI THOẠI: Dịch tự nhiên sang tiếng Việt, thêm mô tả cách nói (thì thầm, hét lên, nghẹn ngào, tức giận, etc.)
4. LIÊN KẾT: Mỗi đoạn phải nối tiếp logic với đoạn trước, tạo dòng chảy câu chuyện mượt mà.
5. PHONG CÁCH: Văn xuôi sinh động, hấp dẫn, giàu cảm xúc, không khô khan liệt kê.

XÁC ĐỊNH TÊN NHÂN VẬT:
- ĐỌC TÊN THẬT của nhân vật từ lời thoại/văn bản trong manga (trong bong bóng hội thoại, khi nhân vật gọi tên nhau)
- SỬ DỤNG ĐÚNG TÊN GỐC (Naruto, Sakura, Luffy, Goku, etc.) - KHÔNG đổi sang tên Việt
- Theo dõi ngoại hình để nhận diện nhân vật khi họ xuất hiện lại
- CHỈ KHI không thấy tên trong manga, mới dùng mô tả ("người đàn ông bí ẩn", "cô gái tóc vàng")

XỬ LÝ ÂM THANH/HIỆU ỨNG:
- Nhận diện âm thanh manga: BANG, CRASH, ドドド, バン, WHOOSH, シュッ, THUD, ドン, ゴゴゴ, etc.
- KHÔNG BAO GIỜ viết nguyên văn âm thanh vào truyện
- Chuyển thành mô tả văn xuôi tiếng Việt:
  • "BANG!/バン" → "Một tiếng nổ chát chúa vang lên"
  • "ドドドド" → "Tiếng bước chân nặng nề rung chuyển mặt đất"
  • "CRASH/ガシャン" → "Tiếng va đập vỡ tan"
  • "WHOOSH/シュッ" → "Tiếng gió rít qua"
  • "AHHH!/きゃー" → "Cô gái thét lên kinh hoàng"
  • "ゴゴゴ" → "Không khí trở nên căng thẳng, đầy đe dọa"

ĐỊNH DẠNG LỜI THOẠI:
- Luôn nêu TÊN NGƯỜI NÓI trước lời thoại
- Format: [Tên nhân vật] [hành động/cảm xúc] nói: "[lời thoại]"
- Ví dụ: Naruto nghiến răng nói: "Tao sẽ không bỏ cuộc!"
- Ví dụ: Sakura lo lắng hỏi: "Cậu có sao không?"

TUYỆT ĐỐI KHÔNG ĐƯỢC:
- Viết lời chào, lời giới thiệu, bình luận, giải thích
- Lặp lại câu hoặc ý đã viết
- Viết "Tôi sẽ...", "Hãy để tôi...", "Được rồi...", hay bất kỳ câu trả lời AI nào
- Tóm tắt sơ sài, phải kể chi tiết
- Viết âm thanh/hiệu ứng nguyên văn (BANG, ドドド, etc.)"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepinfra_api_key,
            base_url=settings.deepinfra_base_url,
        )
        self.content_path = Path(settings.content_dir)
        self.content_path.mkdir(parents=True, exist_ok=True)

    def _build_prompt(self, manga_title: str, part_info: str) -> str:
        """Build the Vietnamese story narration prompt."""
        return f"""Chuyển thể manga "{manga_title}" thành truyện văn xuôi tiếng Việt.

HƯỚNG DẪN CHI TIẾT:
1. Quan sát kỹ từng hình ảnh, xác định các nhân vật chính
2. ĐỌC TÊN NHÂN VẬT từ lời thoại trong manga và sử dụng đúng tên đó (giữ nguyên tên gốc)
3. Bắt đầu bằng việc mô tả bối cảnh/khung cảnh
4. Kể lại hành động và đối thoại theo đúng thứ tự hình ảnh
5. Mô tả biểu cảm, cảm xúc của nhân vật
6. Chuyển âm thanh/hiệu ứng thành mô tả văn xuôi (không viết nguyên văn)

BẮT ĐẦU KỂ CHUYỆN NGAY (không viết lời giới thiệu):
"""

    def _build_continuation_prompt(self, manga_title: str, part_info: str, previous_story: str = "") -> str:
        """Build prompt for continuation parts with context."""
        context_note = ""
        if previous_story:
            # Get last ~800 characters for context
            story_context = previous_story[-800:] if len(previous_story) > 800 else previous_story
            context_note = f"""
CÂU CHUYỆN TRƯỚC ĐÓ (để tiếp nối, giữ nguyên tên nhân vật):
---
{story_context}
---

"""
        return f"""{context_note}Tiếp tục kể câu chuyện "{manga_title}".

LƯU Ý QUAN TRỌNG:
- Giữ nguyên tên các nhân vật đã đặt ở phần trước
- Tiếp nối mạch truyện một cách tự nhiên
- Không lặp lại nội dung đã kể
- Không viết lời chào hay bình luận

TIẾP TỤC CÂU CHUYỆN:
"""

    async def _call_ai_api(self, messages: list, max_tokens: int = 8000, temperature: float = 0.7) -> str:
        """Make a single API call to the AI model."""
        response = await self.client.chat.completions.create(
            model=settings.qwen_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def _extract_story_state(self, story_text: str) -> str:
        """
        Extract structured story state from generated text for context passing.
        This gives the next chunk a clear understanding of where the story is.
        """
        if not story_text or len(story_text) < 200:
            return ""

        # Use last portion of story for extraction
        text_to_analyze = story_text[-2000:] if len(story_text) > 2000 else story_text

        messages = [
            {"role": "system", "content": self.STORY_STATE_PROMPT},
            {"role": "user", "content": f"Đoạn truyện:\n\n{text_to_analyze}"}
        ]

        try:
            result = await self._call_ai_api(messages, max_tokens=500, temperature=0.3)
            logger.info(f"Extracted story state: {result[:150]}...")
            return result
        except Exception as e:
            logger.error(f"Story state extraction error: {e}")
            return ""

    def _build_continuation_prompt_with_state(
        self,
        manga_title: str,
        story_state: str = "",
        last_paragraph: str = ""
    ) -> str:
        """Build continuation prompt with structured story state context."""
        if not last_paragraph:
            last_paragraph = "[Bắt đầu phần mới]"

        context_section = ""
        if story_state:
            context_section = f"""TRẠNG THÁI TRUYỆN HIỆN TẠI:
{story_state}

"""

        return f"""{context_section}ĐOẠN CUỐI PHẦN TRƯỚC:
---
{last_paragraph}
---

Tiếp tục kể câu chuyện "{manga_title}" từ đây.

LƯU Ý QUAN TRỌNG:
- Giữ nguyên tên nhân vật đã xuất hiện trước đó
- Tiếp nối ĐÚNG bối cảnh và không khí đã mô tả
- Không lặp lại nội dung đã kể
- Bắt đầu từ điểm câu chuyện dừng lại

TIẾP TỤC CÂU CHUYỆN:
"""

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

        # Process each chunk with context passing
        all_scripts = []
        story_state = ""  # Structured story state for context
        last_paragraph = ""  # Last paragraph for smooth transition
        previous_images = []  # Store last 5 images from previous chunk

        for chunk_idx, chunk in enumerate(chunks):
            chunk_num = chunk_idx + 1
            logger.info(f"Processing chunk {chunk_num}/{len(chunks)} with {len(chunk)} images")

            # Build content for story generation
            content = []

            if chunk_idx == 0:
                # First chunk - use base prompt
                prompt = self._build_prompt(manga_title, "")
                content.append({
                    "type": "text",
                    "text": prompt
                })
            else:
                # Continuation chunks - add structured story state context
                prompt = self._build_continuation_prompt_with_state(
                    manga_title,
                    story_state,
                    last_paragraph
                )
                content.append({
                    "type": "text",
                    "text": prompt
                })

                # Add last 5 images from previous chunk for visual continuity
                if previous_images:
                    content.append({
                        "type": "text",
                        "text": "\n[HÌNH ẢNH CUỐI TỪ PHẦN TRƯỚC - để nhận diện nhân vật]:\n"
                    })
                    for img in previous_images[-5:]:
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{img['media_type']};base64,{img['base64']}"
                            }
                        })
                    content.append({
                        "type": "text",
                        "text": "\n[HÌNH ẢNH MỚI - tiếp tục kể từ đây]:\n"
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

            # Build messages with improved system prompt
            messages = [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
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

                # Store context for next chunk
                previous_images = [item["image"] for item in chunk]

                # Extract structured story state for next chunk (only if more chunks remain)
                if chunk_idx < len(chunks) - 1:
                    logger.info(f"Extracting story state for chunk {chunk_num}...")
                    story_state = await self._extract_story_state(script)

                    # Extract last paragraph for smooth transition
                    paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
                    if paragraphs:
                        # Get last 2 paragraphs for better context
                        last_paragraph = '\n\n'.join(paragraphs[-2:]) if len(paragraphs) >= 2 else paragraphs[-1]
                        # Limit length
                        if len(last_paragraph) > 500:
                            last_paragraph = last_paragraph[-500:]

                if progress_callback:
                    await progress_callback(chunk_num, len(chunks))

            except Exception as e:
                logger.error(f"AI processing error for chunk {chunk_num}: {e}")
                logger.warning(f"Skipping chunk {chunk_num} due to error")
                # Keep previous context even if this chunk fails
                previous_images = [item["image"] for item in chunk]

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

    REFINE_SYSTEM_PROMPT = """Bạn là biên tập viên chuyên nghiệp. Nhiệm vụ: chỉnh sửa và hoàn thiện câu chuyện manga.

CÔNG VIỆC CỦA BẠN:
1. ĐẢM BẢO NHẤT QUÁN TÊN NHÂN VẬT:
   - Tìm tất cả tên nhân vật được đề cập trong truyện
   - Nếu cùng một nhân vật có nhiều tên khác nhau, chọn tên xuất hiện nhiều nhất và thống nhất
   - Giữ nguyên tên gốc (không đổi sang tên Việt)

2. XỬ LÝ ÂM THANH CÒN SÓT:
   - Tìm và chuyển đổi bất kỳ âm thanh/hiệu ứng nào còn viết nguyên văn (BANG, ドドド, CRASH, etc.)
   - Chuyển thành mô tả văn xuôi tiếng Việt tự nhiên

3. CẢI THIỆN MẠCH TRUYỆN:
   - Loại bỏ câu lặp lại hoặc ý trùng lặp
   - Sửa các đoạn chuyển cảnh không mượt mà
   - Đảm bảo logic liên kết giữa các đoạn

4. POLISH VĂN PHONG:
   - Sửa câu văn lủng củng, khó đọc
   - Giữ phong cách kể chuyện sinh động, hấp dẫn

TUYỆT ĐỐI KHÔNG ĐƯỢC:
- Thêm nội dung mới không có trong truyện gốc
- Viết lời bình luận, giải thích
- Rút ngắn hoặc tóm tắt truyện
- Thay đổi cốt truyện

CHỈ TRẢ VỀ TRUYỆN ĐÃ CHỈNH SỬA, KHÔNG VIẾT GÌ THÊM."""

    async def refine_script(self, script_content: str, manga_title: str) -> str:
        """
        Final refinement pass on the complete story before TTS.
        - Ensures character name consistency
        - Cleans up any remaining raw sound effects
        - Improves flow and removes repetition
        - Polishes overall narrative
        """
        if not script_content or len(script_content) < 100:
            return script_content

        logger.info(f"Starting script refinement for '{manga_title}' ({len(script_content)} chars)")

        # For very long scripts, process in chunks to avoid token limits
        MAX_CHARS_PER_CALL = 15000

        if len(script_content) <= MAX_CHARS_PER_CALL:
            # Process entire script in one call
            refined = await self._refine_chunk(script_content, manga_title)
        else:
            # Split into chunks at paragraph boundaries
            chunks = self._split_for_refinement(script_content, MAX_CHARS_PER_CALL)
            logger.info(f"Script too long, splitting into {len(chunks)} chunks for refinement")

            refined_chunks = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Refining chunk {i + 1}/{len(chunks)}")
                refined_chunk = await self._refine_chunk(chunk, manga_title)
                refined_chunks.append(refined_chunk)

            refined = "\n\n".join(refined_chunks)

        logger.info(f"Refinement complete: {len(script_content)} -> {len(refined)} chars")
        return refined

    def _split_for_refinement(self, text: str, max_chars: int) -> list:
        """Split text into chunks at paragraph boundaries."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def _refine_chunk(self, chunk: str, manga_title: str) -> str:
        """Refine a single chunk of the script."""
        messages = [
            {
                "role": "system",
                "content": self.REFINE_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"""Chỉnh sửa và hoàn thiện đoạn truyện manga "{manga_title}" sau đây:

---
{chunk}
---

Trả về bản đã chỉnh sửa:"""
            }
        ]

        try:
            response = await self.client.chat.completions.create(
                model=settings.qwen_model,
                messages=messages,
                max_tokens=16000,
                temperature=0.3,  # Lower temperature for more consistent editing
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Refinement API error: {e}")
            return chunk  # Return original if refinement fails

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
