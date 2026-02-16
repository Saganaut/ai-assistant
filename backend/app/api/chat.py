from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.llm.base import Message
from app.services.llm.gemini import GeminiProvider

router = APIRouter()


def get_llm_provider():
    # TODO: factory based on settings.llm_provider
    return GeminiProvider()


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    provider = get_llm_provider()
    messages: list[Message] = []

    try:
        while True:
            data = await websocket.receive_text()
            messages.append(Message(role="user", content=data))

            full_response = ""
            async for token in provider.chat_stream(messages):
                await websocket.send_text(token)
                full_response += token

            # Send end-of-message marker
            await websocket.send_json({"type": "end"})
            messages.append(Message(role="assistant", content=full_response))
    except WebSocketDisconnect:
        pass
