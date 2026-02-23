# AnCapTruyenLamVideo - Text-to-Speech Service

import logging
import asyncio
from pathlib import Path
from typing import Optional

import edge_tts

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSService:
    """Text-to-Speech service using Edge TTS for Vietnamese narration."""

    # Vietnamese voices available in Edge TTS
    VIETNAMESE_VOICES = {
        "female": "vi-VN-HoaiMyNeural",  # Female voice
        "male": "vi-VN-NamMinhNeural",    # Male voice
    }

    def __init__(self):
        self.output_path = Path(settings.content_dir)
        self.default_voice = self.VIETNAMESE_VOICES["male"]

    async def generate_audio(
        self,
        text: str,
        output_file: Path,
        voice: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> bool:
        """
        Generate audio from text using Edge TTS.

        Args:
            text: Text to convert to speech
            output_file: Path to save the audio file (mp3)
            voice: Voice to use (default: Vietnamese female)
            rate: Speech rate adjustment (e.g., "+10%", "-10%")
            volume: Volume adjustment (e.g., "+10%", "-10%")

        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return False

        voice = voice or self.default_voice

        try:
            # Create output directory if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Generate speech
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume
            )

            await communicate.save(str(output_file))
            logger.info(f"Generated audio: {output_file}")
            return True

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False

    async def generate_audio_for_segments(
        self,
        segments: list[dict],
        output_dir: Path,
        voice: Optional[str] = None
    ) -> list[dict]:
        """
        Generate audio for multiple text segments.

        Args:
            segments: List of {text: str, chapter: str, index: int}
            output_dir: Directory to save audio files
            voice: Voice to use

        Returns:
            List of {audio_path: str, duration: float, ...} for each segment
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for i, segment in enumerate(segments):
            text = segment.get("text", "")
            if not text.strip():
                continue

            audio_file = output_dir / f"segment_{i:04d}.mp3"

            success = await self.generate_audio(
                text=text,
                output_file=audio_file,
                voice=voice
            )

            if success:
                # Get audio duration using ffprobe
                duration = await self._get_audio_duration(audio_file)
                results.append({
                    **segment,
                    "audio_path": str(audio_file),
                    "duration": duration
                })
            else:
                logger.warning(f"Failed to generate audio for segment {i}")

        return results

    async def _get_audio_duration(self, audio_file: Path) -> float:
        """Get duration of audio file in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_file)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return float(stdout.decode().strip())
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return 5.0  # Default duration

    async def list_voices(self) -> list[dict]:
        """List available Vietnamese voices."""
        voices = await edge_tts.list_voices()
        vietnamese_voices = [v for v in voices if v["Locale"].startswith("vi-")]
        return vietnamese_voices


# Singleton instance
tts_service = TTSService()
