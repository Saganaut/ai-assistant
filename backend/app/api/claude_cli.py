from fastapi import APIRouter, WebSocket

from app.api.cli_ws import run_cli_over_ws

router = APIRouter()


@router.websocket("/claude")
async def claude_cli_ws(websocket: WebSocket):
    await run_cli_over_ws(websocket, "claude")


@router.websocket("/gemini")
async def gemini_cli_ws(websocket: WebSocket):
    await run_cli_over_ws(websocket, "gemini")
