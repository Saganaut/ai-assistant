# AI Assistant

A self-hosted personal AI assistant with a web dashboard. Deployed on a home server, accessed remotely via Tailscale.

## Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- npm

## Setup

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
uv sync
```

### Frontend

```bash
cd frontend
npm install
```

## Running

### Backend

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm run dev
```

### Both (quick start)

From the project root, run in two terminals:

```bash
# Terminal 1 - Backend
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/chat/ws` | WebSocket | Chat with AI (streaming) |
| `/api/files/list?path=` | GET | List files in sandbox |
| `/api/files/read?path=` | GET | Read a file from sandbox |
| `/api/files/write` | POST | Write a file to sandbox |

## Environment Variables

All prefixed with `ASSISTANT_`. See `backend/.env.example` for the full list.

| Variable | Description |
|---|---|
| `ASSISTANT_GEMINI_API_KEY` | Google Gemini API key |
| `ASSISTANT_ELEVENLABS_API_KEY` | ElevenLabs TTS API key |
| `ASSISTANT_GITHUB_TOKEN` | GitHub personal access token |
| `ASSISTANT_GOOGLE_CREDENTIALS_PATH` | Path to Google service account JSON |
| `ASSISTANT_LLM_PROVIDER` | LLM provider: `gemini`, `openai`, `local` |
| `ASSISTANT_TTS_PROVIDER` | TTS provider: `elevenlabs`, `local` |

## Project Structure

```
ai-assistant/
├── backend/           # FastAPI + Python
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── core/      # Config, database, sandbox
│   │   ├── models/    # SQLModel definitions
│   │   └── services/  # LLM, voice, integrations, scheduler
│   └── data/          # Sandboxed file storage (LLM access)
├── frontend/          # React + TypeScript + Vite
│   └── src/
│       └── components/
├── docs/              # Architecture, roadmap, decisions
└── shared/            # Shared types (future)
```

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Tech Decisions](docs/TECH_DECISIONS.md)
