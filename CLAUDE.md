# AI Assistant - Project Guide

## Project Overview

Personal AI assistant with web dashboard, deployed on home server, accessed via Tailscale.

## Stack
- **Frontend:** React + TypeScript, CSS Modules, npm
- **Backend:** FastAPI (Python), uv, SQLite
- **LLM:** Gemini API (swappable via provider abstraction)
- **Voice:** Whisper STT (local), ElevenLabs TTS (swappable)

## Structure
- Monorepo: `frontend/`, `backend/`, `docs/`, `shared/`
- Backend sandboxed data folder: `backend/data/`

## Key Conventions
- Dark mode default
- No Tailwind - use CSS Modules
- All LLM/voice providers behind abstract interfaces
- File access MUST be sandboxed to `backend/data/`
- No auth on web UI (Tailscale-only access)
- API keys in environment variables, never in code or frontend

## Commands
- Frontend: `cd frontend && npm run dev`
- Backend: `cd backend && uv run uvicorn app.main:app --reload`
- Tests: `cd backend && uv run pytest tests/ -v`

## Docs
- `docs/ARCHITECTURE.md` - system architecture and design
- `docs/ROADMAP.md` - feature roadmap by version
- `docs/TECH_DECISIONS.md` - decision log
