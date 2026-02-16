"""Voice provider factory."""

from app.core.config import settings
from app.services.voice.base import BaseSTTProvider, BaseTTSProvider


def get_stt_provider() -> BaseSTTProvider:
    """Always returns the local Whisper provider."""
    from app.services.voice.whisper_stt import WhisperSTTProvider
    return WhisperSTTProvider()


def get_tts_provider() -> BaseTTSProvider:
    """Returns the configured TTS provider."""
    if settings.tts_provider == "elevenlabs":
        from app.services.voice.elevenlabs_tts import ElevenLabsTTSProvider
        return ElevenLabsTTSProvider()
    else:
        raise ValueError(f"Unknown TTS provider: {settings.tts_provider}")
