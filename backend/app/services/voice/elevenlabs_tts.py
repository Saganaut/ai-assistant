"""ElevenLabs TTS provider."""

import httpx

from app.core.config import settings
from app.services.voice.base import BaseTTSProvider


class ElevenLabsTTSProvider(BaseTTSProvider):
    """Text-to-speech using ElevenLabs API."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        # Default voice is "Rachel"
        self._voice_id = voice_id

    async def synthesize(self, text: str) -> bytes:
        if not settings.elevenlabs_api_key:
            raise RuntimeError("ElevenLabs API key not configured")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/text-to-speech/{self._voice_id}",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.content

    def audio_mime_type(self) -> str:
        return "audio/mpeg"
