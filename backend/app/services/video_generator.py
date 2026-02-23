# AnCapTruyenLamVideo - Video Generator Service

import asyncio
import logging
import re
import shutil
from pathlib import Path
from typing import Optional, Callable, List
from datetime import datetime

from ..config import get_settings
from .tts_service import tts_service

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoGenerator:
    """Generates video from manga images and story script."""

    def __init__(self):
        self.content_path = Path(settings.content_dir)
        self.images_path = Path(settings.images_dir)
        self.videos_path = Path(settings.videos_dir)
        self.temp_path = Path("temp_video")
        # Ensure videos directory exists
        self.videos_path.mkdir(parents=True, exist_ok=True)

    async def generate_video(
        self,
        task_id: str,
        manga_title: str,
        script_content: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        Generate video from manga images and story script.

        Args:
            task_id: Task ID for locating images
            manga_title: Title of the manga
            script_content: The story script text
            progress_callback: Callback for progress updates

        Returns:
            Path to generated video file, or None if failed
        """
        task_images_path = self.images_path / task_id
        task_output_path = self.videos_path / task_id
        task_temp_path = self.temp_path / task_id

        # Clean up temp directory
        if task_temp_path.exists():
            shutil.rmtree(task_temp_path)
        task_temp_path.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Collect all images in order
            if progress_callback:
                await progress_callback("collecting_images", 5)

            all_images = self._collect_images(task_images_path)
            if not all_images:
                logger.error("No images found for video generation")
                return None

            logger.info(f"Found {len(all_images)} images for video")
            if len(all_images) > 100:
                logger.info(f"Large video: this may take 10-30 minutes to process")

            # Step 2: Generate full audio from script
            if progress_callback:
                await progress_callback("generating_audio", 10)

            # Clean script for TTS (remove headers, markers, etc.)
            clean_script = self._clean_script_for_tts(script_content)
            logger.info(f"Cleaned script: {len(clean_script)} characters for TTS")

            audio_file = task_temp_path / "narration.mp3"
            logger.info("Starting audio generation (this may take a few minutes)...")
            success = await tts_service.generate_audio(
                text=clean_script,
                output_file=audio_file
            )

            if not success:
                logger.error("Failed to generate audio")
                return None

            # Get audio duration
            audio_duration = await tts_service._get_audio_duration(audio_file)
            logger.info(f"Generated audio: {audio_duration:.2f} seconds")

            if progress_callback:
                await progress_callback("audio_complete", 40)

            # Step 3: Calculate duration per image
            duration_per_image = audio_duration / len(all_images)
            # Minimum 2 seconds per image, maximum 10 seconds
            duration_per_image = max(2.0, min(10.0, duration_per_image))

            logger.info(f"Duration per image: {duration_per_image:.2f} seconds")

            # Step 4: Create video from images
            if progress_callback:
                await progress_callback("creating_video", 50)

            # Create image list file for ffmpeg
            image_list_file = task_temp_path / "images.txt"
            await self._create_image_list(all_images, image_list_file, duration_per_image)

            # Generate video
            output_video = task_output_path / f"{self._sanitize_filename(manga_title)}_video.mp4"
            output_video.parent.mkdir(parents=True, exist_ok=True)

            success = await self._create_video_with_ffmpeg(
                image_list_file=image_list_file,
                audio_file=audio_file,
                output_file=output_video,
                total_images=len(all_images),
                progress_callback=progress_callback
            )

            if success:
                logger.info(f"Video generated: {output_video}")
                if progress_callback:
                    await progress_callback("video_complete", 100)
                return str(output_video)
            else:
                logger.error("Failed to create video")
                return None

        except Exception as e:
            logger.error(f"Video generation error: {e}")
            return None

        finally:
            # Clean up temp files
            if task_temp_path.exists():
                shutil.rmtree(task_temp_path)

    def _collect_images(self, images_path: Path) -> List[Path]:
        """Collect all images from chapter directories in order."""
        if not images_path.exists():
            return []

        all_images = []

        # Get chapter directories sorted by chapter number
        chapter_dirs = sorted(
            [d for d in images_path.iterdir() if d.is_dir()],
            key=lambda x: self._parse_chapter_number(x.name)
        )

        for chapter_dir in chapter_dirs:
            # Get images in this chapter, sorted by name
            chapter_images = sorted(
                [f for f in chapter_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']],
                key=lambda x: x.name
            )
            all_images.extend(chapter_images)

        return all_images

    def _parse_chapter_number(self, name: str) -> float:
        """Parse chapter number from directory name."""
        # Replace underscores back to dots for proper sorting
        name = name.replace("_", ".")
        match = re.search(r"(\d+(?:\.\d+)?)", name)
        if match:
            return float(match.group(1))
        return 0.0

    def _clean_script_for_tts(self, script: str) -> str:
        """Clean script content for text-to-speech."""
        lines = script.split("\n")
        clean_lines = []

        # Phrases to skip (meta/conversation phrases)
        skip_phrases = [
            "Tất nhiên rồi",
            "Hãy để tôi",
            "Tôi sẽ tiếp tục",
            "Tôi sẽ kể",
            "Được rồi",
            "Chắc chắn rồi",
            "Như bạn yêu cầu",
            "Theo yêu cầu",
            "Dưới đây là",
            "Đây là phần",
            "Tiếp tục từ",
            "BẮT ĐẦU VIẾT",
            "TIẾP TỤC:",
            "CÂU CHUYỆN:",
        ]

        for line in lines:
            stripped = line.strip()

            # Skip separator lines (=== or ---)
            if stripped.startswith("===") or stripped.startswith("---"):
                continue

            # Skip part markers like "PHẦN 3/45"
            if re.match(r"^PHẦN\s*\d+/\d+", stripped):
                continue

            # Skip empty lines at the start
            if not clean_lines and not stripped:
                continue

            # Skip metadata lines (fallback, should not appear in clean script)
            if any(x in line for x in ["Task ID:", "Batch:", "Chapters:", "Generated:", "Total Batches:", "Manga:"]):
                continue

            # Skip meta/conversation phrases
            if any(phrase in stripped for phrase in skip_phrases):
                continue

            # Skip chapter markers but add natural chapter reference
            if stripped.startswith("CHƯƠNG") or stripped.startswith("--- CHƯƠNG"):
                match = re.search(r"CHƯƠNG\s*(\d+)", stripped)
                if match:
                    clean_lines.append(f"Chương {match.group(1)}.")
                continue

            clean_lines.append(line)

        # Join lines
        text = "\n".join(clean_lines)

        # Remove duplicate sentences (track all seen, not just consecutive)
        sentences = re.split(r'([.!?]+)', text)
        seen_sentences = set()
        cleaned_sentences = []

        i = 0
        while i < len(sentences):
            sentence = sentences[i].strip()
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""

            if sentence:
                # Normalize for comparison
                normalized = re.sub(r'\s+', ' ', sentence.lower().strip())

                if normalized not in seen_sentences:
                    seen_sentences.add(normalized)
                    cleaned_sentences.append(sentence + punct)

            i += 2 if punct else 1

        text = " ".join(cleaned_sentences)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        return text.strip()

    async def _create_image_list(
        self,
        images: List[Path],
        output_file: Path,
        duration: float
    ):
        """Create ffmpeg concat demuxer input file."""
        with open(output_file, "w") as f:
            for img in images:
                # Escape single quotes in path
                escaped_path = str(img.absolute()).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
                f.write(f"duration {duration}\n")

            # Add last image again (required by concat demuxer)
            if images:
                escaped_path = str(images[-1].absolute()).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

    async def _create_video_with_ffmpeg(
        self,
        image_list_file: Path,
        audio_file: Path,
        output_file: Path,
        total_images: int = 0,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Create video using ffmpeg with progress streaming."""
        try:
            # Build ffmpeg command with progress output
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-progress", "pipe:1",  # Output progress to stdout
                "-f", "concat",
                "-safe", "0",
                "-i", str(image_list_file),
                "-i", str(audio_file),
                "-c:v", "libx264",
                "-preset", "fast",  # Use fast preset for quicker encoding
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-shortest",
                "-movflags", "+faststart",
                str(output_file)
            ]

            logger.info(f"Running ffmpeg with {total_images} images...")
            logger.info(f"This may take several minutes for large videos...")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Stream progress from stdout
            last_progress_log = 0
            frame_count = 0

            async def read_progress():
                nonlocal last_progress_log, frame_count
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    line_str = line.decode().strip()
                    if line_str.startswith("frame="):
                        try:
                            frame_count = int(line_str.split("=")[1])
                            # Log progress every 100 frames
                            if frame_count - last_progress_log >= 100:
                                if total_images > 0:
                                    pct = min(99, int((frame_count / total_images) * 100))
                                    logger.info(f"Video encoding: {frame_count}/{total_images} frames ({pct}%)")
                                    if progress_callback:
                                        await progress_callback("encoding_video", 50 + int(pct * 0.45))
                                else:
                                    logger.info(f"Video encoding: {frame_count} frames processed")
                                last_progress_log = frame_count
                        except (ValueError, IndexError):
                            pass

            # Read stderr for errors
            async def read_stderr():
                stderr_data = []
                while True:
                    line = await proc.stderr.readline()
                    if not line:
                        break
                    stderr_data.append(line.decode())
                return "".join(stderr_data)

            # Run both readers concurrently
            _, stderr_output = await asyncio.gather(
                read_progress(),
                read_stderr()
            )

            await proc.wait()

            if proc.returncode != 0:
                logger.error(f"ffmpeg error: {stderr_output}")
                return False

            logger.info(f"Video encoding complete: {frame_count} total frames")
            return True

        except Exception as e:
            logger.error(f"ffmpeg execution error: {e}")
            return False

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove or replace invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.replace(' ', '_')
        return name[:100]  # Limit length


# Singleton instance
video_generator = VideoGenerator()
