"""Voice API - push-to-talk STT and TTS synthesis.

Flow:
1. Client records audio (push-to-talk) and sends it as binary via WebSocket
2. Server transcribes with Whisper (local)
3. Transcribed text is sent back as a text message
4. Client can also request TTS for any text via a REST endpoint
"""

import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.voice import get_stt_provider, get_tts_provider

logger = logging.getLogger(__name__)

router = APIRouter()


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    """Synthesize text to speech. Returns audio bytes."""
    try:
        provider = get_tts_provider()
        audio_bytes = await provider.synthesize(body.text)
        return Response(content=audio_bytes, media_type=provider.audio_mime_type())
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return Response(content=str(e), status_code=500)


@router.websocket("/ws")
async def voice_websocket(websocket: WebSocket):
    """WebSocket for push-to-talk audio streaming.

    Client sends binary audio data (recorded from microphone).
    Server responds with JSON: {"type": "transcription", "text": "..."}
    """
    await websocket.accept()
    stt = get_stt_provider()

    try:
        while True:
            # Receive audio data
            data = await websocket.receive()

            if "bytes" in data:
                audio_bytes = data["bytes"]
            elif "text" in data:
                # Could be a JSON message with base64 audio
                try:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "audio" and msg.get("data"):
                        audio_bytes = base64.b64decode(msg["data"])
                    else:
                        continue
                except (json.JSONDecodeError, KeyError):
                    continue
            else:
                continue

            if not audio_bytes:
                continue

            # Transcribe
            try:
                text = await stt.transcribe(audio_bytes)
                await websocket.send_json({
                    "type": "transcription",
                    "text": text,
                })
            except Exception as e:
                logger.error(f"STT error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        pass
