"""Local Whisper STT provider using the openai-whisper library or faster-whisper."""

import asyncio
import logging
import tempfile
from pathlib import Path

from app.services.voice.base import BaseSTTProvider

logger = logging.getLogger(__name__)


class WhisperSTTProvider(BaseSTTProvider):
    """Local Whisper speech-to-text using faster-whisper."""

    def __init__(self, model_size: str = "base"):
        self._model_size = model_size
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(self._model_size, device="auto", compute_type="auto")
                logger.info(f"Loaded Whisper model: {self._model_size}")
            except ImportError:
                raise RuntimeError(
                    "faster-whisper is not installed. Run: uv add faster-whisper"
                )

    async def transcribe(self, audio_data: bytes, mime_type: str = "audio/webm") -> str:
        self._ensure_model()

        # Write audio to temp file (whisper needs a file path)
        suffix = ".webm" if "webm" in mime_type else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            segments, _ = await asyncio.to_thread(
                self._model.transcribe,  # type: ignore
                temp_path,
                language="en",
            )
            text = " ".join(segment.text for segment in segments)
            return text.strip()
        finally:
            Path(temp_path).unlink(missing_ok=True)
