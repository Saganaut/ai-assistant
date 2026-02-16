# AI Assistant

A self-hosted personal AI assistant with a web dashboard. Deployed on a home server, accessed remotely via Tailscale.

## Features

- **Chat with AI** - Streaming chat powered by Google Gemini (swappable to other LLMs)
- **25 Agent Tools** - File management, web browsing/search, notes, bookmarks, health logging
- **Google Integration** - Calendar, Drive, Gmail via OAuth token
- **GitHub Integration** - Projects (kanban), repos, issues via GraphQL + REST
- **Voice** - Push-to-talk with Whisper STT (local) and ElevenLabs TTS
- **Scheduled Actions** - Cron-based automation (morning briefings, daily summaries, inbox triage)
- **Mobile Friendly** - Responsive layout with floating chat button
- **Sandboxed Files** - LLM file access is hard-sandboxed to `backend/data/`
- **Dark Mode** - Default dark theme

## Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- npm

### Optional (for voice)

```bash
cd backend && uv sync --extra voice
```

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
| `/api/chat/ws` | WebSocket | Chat with AI (streaming + tool use) |
| `/api/voice/ws` | WebSocket | Push-to-talk audio transcription |
| `/api/voice/tts` | POST | Text-to-speech synthesis |
| `/api/conversations/` | GET | List conversations |
| `/api/conversations/{id}` | GET/DELETE | Get or delete conversation |
| `/api/files/list` | GET | List files in sandbox |
| `/api/files/read` | GET | Read a file from sandbox |
| `/api/files/write` | POST | Write a file to sandbox |
| `/api/files/upload` | POST | Upload a file to sandbox |
| `/api/files/mkdir` | POST | Create directory in sandbox |
| `/api/files/delete` | DELETE | Delete file/directory in sandbox |
| `/api/notes/list` | GET | List note files |
| `/api/notes/read` | GET | Read a note |
| `/api/notes/quick` | POST | Create a quick note |
| `/api/notes/health` | POST | Create a health log entry |
| `/api/google/status` | GET | Check Google auth status |
| `/api/google/token` | POST | Set Google OAuth token |
| `/api/schedules/` | GET/POST | List or create scheduled actions |
| `/api/schedules/{id}` | PATCH/DELETE | Update or delete schedule |
| `/api/schedules/{id}/runs` | GET | View schedule run history |
| `/api/schedules/templates` | GET | Get built-in schedule templates |

## Agent Tools (25)

**Files:** `read_file`, `write_file`, `list_files`, `search_files`
**Web:** `web_browse`, `web_search`, `save_bookmark`
**Notes:** `quick_note`, `health_note`, `read_notes`
**Google:** `google_calendar_list`, `google_calendar_create`, `google_calendar_delete`, `google_drive_list`, `google_drive_search`, `google_gmail_list`, `google_gmail_read`, `google_gmail_send`
**GitHub:** `github_repos_list`, `github_issues_list`, `github_issues_create`, `github_repos_read_file`, `github_projects_list`, `github_projects_items`, `github_projects_add_item`

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
├── backend/
│   ├── app/
│   │   ├── api/            # REST + WebSocket route handlers
│   │   ├── core/           # Config, database, sandbox
│   │   ├── models/         # SQLModel (conversations, schedules)
│   │   └── services/
│   │       ├── llm/        # LLM provider abstraction
│   │       ├── voice/      # STT/TTS provider abstraction
│   │       ├── tools/      # Agent tool definitions
│   │       ├── integrations/ # Google, GitHub API clients
│   │       └── scheduler/  # Cron-based background scheduler
│   └── data/               # Sandboxed file storage
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Chat/       # Chat panel + voice button
│       │   ├── Dashboard/  # Kanban, calendar, notes, scheduler, files
│       │   ├── FileBrowser/ # Sandboxed file browser
│       │   └── Layout/     # Main layout, header, settings
│       └── services/       # API client
├── docs/
└── shared/
```

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Tech Decisions](docs/TECH_DECISIONS.md)
