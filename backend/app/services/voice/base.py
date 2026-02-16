"""Abstract voice provider interfaces for STT and TTS."""

from abc import ABC, abstractmethod


class BaseSTTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_data: bytes, mime_type: str = "audio/webm") -> str:
        """Transcribe audio data to text."""
        ...


class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio. Returns audio bytes (mp3 or wav)."""
        ...

    @abstractmethod
    def audio_mime_type(self) -> str:
        """Return the MIME type of the synthesized audio."""
        ...
