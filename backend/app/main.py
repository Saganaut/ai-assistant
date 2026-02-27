import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import chat, claude_cli, conversations, files, google_auth, integrations, markets, notes, schedules, voice, workouts
from app.services.scheduler.scheduler import scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging based on debug setting
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s" if settings.debug
        else "%(levelname)-8s %(name)s: %(message)s",
    )

    init_db()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Start background scheduler
    scheduler_task = asyncio.create_task(scheduler_loop())

    yield

    # Cancel scheduler on shutdown
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(claude_cli.router, prefix="/api/chat", tags=["claude-cli"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
app.include_router(google_auth.router, prefix="/api/google", tags=["google"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(schedules.router, prefix="/api/schedules", tags=["schedules"])
app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
app.include_router(workouts.router, prefix="/api/workouts", tags=["workouts"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
