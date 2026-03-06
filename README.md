# AI Assistant

A self-hosted personal AI assistant with a web dashboard. Deployed on a home server, accessed remotely via Tailscale.

## Features

- **Chat with AI** - Streaming chat powered by Google Gemini (swappable to other LLMs)
- **Agent Tools** - File management, web browsing/search, notes, health logging, calendar, GitHub, WordPress
- **CLI Terminal** - Embedded xterm.js terminal for `/claude` and `/gemini` CLI with session persistence
- **Dashboard Modes** - Overview, Health, and Work modes with different widget layouts
- **Workout Tracker** - BWF Recommended Routine tracker with set/rep logging, progression selection, and local draft persistence
- **Google Integration** - Calendar, Drive, Gmail via OAuth token
- **GitHub Integration** - Projects (kanban), repos, issues via GraphQL + REST
- **WordPress Integration** - Create, edit, and publish posts with media upload
- **Voice** - Push-to-talk with Web Speech API (primary) / Whisper STT fallback, ElevenLabs TTS
- **Scheduled Actions** - Cron-based automation (morning briefings, daily summaries, inbox triage)
- **Debug Panel** - In-browser error log that captures console errors and unhandled rejections (toggled via Settings)
- **Mobile Friendly** - Responsive layout with floating chat button and collapsible widgets
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

## Remote Access (Tailscale HTTPS)

To access the app from your phone or other devices over Tailscale with HTTPS (required for voice/microphone):

1. **Enable HTTPS** in the [Tailscale admin DNS settings](https://login.tailscale.com/admin/dns)

2. **Start the frontend and backend** as usual (see [Running](#running))

3. **Set up Tailscale Serve** to proxy both on a single HTTPS origin:

```bash
# Serve frontend at root
tailscale serve --https=443 / http://localhost:5173

# Proxy /api to the backend
tailscale serve --https=443 /api http://localhost:8000/api
```

4. **Access the app** at `https://<machine>.<tailnet>.ts.net`

This is needed because the Web Speech API and microphone access (`getUserMedia`) both require a secure context (HTTPS or localhost). Without it, the voice button won't work on mobile.

To check your current serve config: `tailscale serve status`
To reset: `tailscale serve reset`

## Dashboard Modes

Switch modes via the gear icon (Settings → Mode):

| Mode | Widgets |
|------|---------|
| **Overview** | All widgets in a draggable grid (Markets, Calendar, Kanban, WordPress, Scheduler, Notes, Files) |
| **Health** | Calendar · Notes (tabbed/collapsible) + WorkoutWidget full-width |
| **Work** | Calendar · Kanban · Scheduler · Notes in a draggable grid |

The selected mode persists in `localStorage`.

## Workout Tracker

Available in Health mode. Implements the [BWF Recommended Routine](https://www.reddit.com/r/bodyweightfitness/wiki/kb/recommended_routine/) with:

- Warm-up, Strength (paired exercises), and Cool-down sections
- Progression selector for each exercise (numbered levels 0, 1, 2…)
- Per-set reps and weight inputs; add/remove sets freely
- Notes field per exercise (contextual tips from the routine)
- "Save Workout" → stored in `backend/data/workouts/YYYY-MM-DD.json`
- Recent sessions list (last 30 days) with completion indicators
- **Draft persistence** — workout state is auto-saved to `localStorage` every change and reloaded on page refresh. Drafts expire after 3 hours (one workout session maximum).
- **Routine editor** — create and edit routines via the ✏ button; full CRUD with section/exercise/progression management

Routines are stored as JSON files in `backend/data/workouts/routines/`. The BWF RR is seeded automatically on first launch.

## CLI Terminal

Type `/claude` or `/gemini` in the chat input to open an embedded terminal running the respective AI CLI.

- Full xterm.js terminal with color support (`TERM=xterm-256color`, `COLORTERM=truecolor`)
- **Session persistence** — navigating away does not kill the process. The backend keeps the PTY alive for 60 seconds after disconnect. Reconnecting within that window resumes the session seamlessly.
- Automatic reconnect with exponential backoff on unexpected disconnects
- Terminal resize is forwarded to the PTY in real-time

## Debug Mode

Enable the in-browser error panel via **Settings → Developer → Debug mode**.

When on, an **Errors** button appears in the header. It shows a live count badge and opens a log of:
- `console` — captured `console.error()` calls
- `unhandled` — uncaught promise rejections and window errors
- `api` — explicit API error events

The log holds up to 100 entries (circular buffer). Use "Clear all" to reset.

Backend verbose logging is controlled separately via the `.env` flag:

```
ASSISTANT_DEBUG=true
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
| `/api/workouts/routines` | GET/POST | List or create workout routines |
| `/api/workouts/routines/{id}` | GET/PUT/DELETE | Get, update, or delete a routine |
| `/api/workouts/logs` | GET/POST | Get log for a date / save today's log |
| `/api/workouts/recent` | GET | List dates with saved workout logs (last 30 days) |
| `/api/cli/claude` | WebSocket | Claude CLI PTY session |
| `/api/cli/gemini` | WebSocket | Gemini CLI PTY session |

## Agent Tools

**Files:** `read_file`, `write_file`, `list_files`, `search_files`
**Web:** `web_browse`, `web_search`, `save_bookmark`
**Notes:** `quick_note`, `health_note`, `read_notes`
**Google:** `google_calendar_list`, `google_calendar_create`, `google_calendar_delete`, `google_drive_list`, `google_drive_search`, `google_gmail_list`, `google_gmail_read`, `google_gmail_send`
**GitHub:** `github_repos_list`, `github_issues_list`, `github_issues_create`, `github_repos_read_file`, `github_projects_list`, `github_projects_items`, `github_projects_add_item`
**WordPress:** `wordpress_list_posts`, `wordpress_get_post`, `wordpress_create_post`, `wordpress_update_post`, `wordpress_delete_post`, `wordpress_upload_media`

## Environment Variables

All prefixed with `ASSISTANT_`. See `backend/.env.example` for the full list.

| Variable | Description |
|---|---|
| `ASSISTANT_GEMINI_API_KEY` | Google Gemini API key |
| `ASSISTANT_ELEVENLABS_API_KEY` | ElevenLabs TTS API key |
| `ASSISTANT_GITHUB_TOKEN` | GitHub personal access token |
| `ASSISTANT_GOOGLE_CREDENTIALS_PATH` | Path to Google service account JSON |
| `ASSISTANT_WORDPRESS_URL` | WordPress site URL |
| `ASSISTANT_WORDPRESS_USERNAME` | WordPress username |
| `ASSISTANT_WORDPRESS_APP_PASSWORD` | WordPress application password |
| `ASSISTANT_LLM_PROVIDER` | LLM provider: `gemini`, `openai`, `local` |
| `ASSISTANT_TTS_PROVIDER` | TTS provider: `elevenlabs`, `local` |
| `ASSISTANT_DEBUG` | Set to `true` for verbose backend logging |

## Project Structure

```
ai-assistant/
├── backend/
│   ├── app/
│   │   ├── api/            # REST + WebSocket route handlers
│   │   │   ├── chat.py
│   │   │   ├── claude_cli.py   # /claude and /gemini CLI endpoints
│   │   │   ├── cli_ws.py       # PTY ↔ WebSocket bridge (session registry)
│   │   │   ├── conversations.py
│   │   │   ├── files.py
│   │   │   ├── integrations.py
│   │   │   ├── notes.py
│   │   │   ├── voice.py
│   │   │   ├── workouts.py     # Workout routine + log CRUD
│   │   │   └── ...
│   │   ├── core/           # Config, database, sandbox
│   │   ├── models/         # SQLModel (conversations, schedules)
│   │   └── services/
│   │       ├── llm/        # LLM provider abstraction
│   │       ├── voice/      # STT/TTS provider abstraction
│   │       ├── tools/      # Agent tool definitions
│   │       ├── integrations/ # Google, GitHub, WordPress API clients
│   │       └── scheduler/  # Cron-based background scheduler
│   ├── data/               # Sandboxed file storage
│   │   └── workouts/
│   │       ├── routines/   # Routine JSON files (one per routine)
│   │       └── YYYY-MM-DD.json  # Daily workout logs
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Chat/       # Chat panel, voice button, CLI terminal (xterm.js)
│       │   ├── Dashboard/  # Kanban, calendar, notes, scheduler, files, workout
│       │   │   ├── WorkoutWidget.tsx   # BWF RR tracker
│       │   │   ├── RoutineEditor.tsx   # Routine CRUD modal
│       │   │   └── DraggableGrid.tsx   # Drag-and-drop widget grid
│       │   └── Layout/     # Header, settings modal, error log modal
│       ├── contexts/
│       │   └── ModeContext.tsx   # Overview / Health / Work mode
│       ├── services/       # API client (including workout helpers)
│       └── utils/
│           ├── logger.ts        # Dev-only console logger
│           └── errorLog.ts      # In-browser error capture for debug panel
├── docs/
└── shared/
```

## Testing

Backend tests use pytest with pytest-asyncio. Install dev dependencies first:

```bash
cd backend && uv sync --extra dev
```

Run the test suite:

```bash
cd backend && uv run pytest tests/ -v
```

### Test Structure

```
backend/tests/
├── conftest.py                    # Fixtures: in-memory DB, mock agent, test client
├── test_api_health.py             # Health endpoint
├── test_api_conversations.py      # Conversation CRUD + 404 handling
└── test_websocket_chat.py         # WebSocket chat: streaming, persistence, multi-turn
```

### Writing New Tests

- All tests use an in-memory SQLite database (auto-reset per test via the `setup_test_db` fixture)
- Use the `client` fixture for a pre-configured `TestClient` with mocked agent, patched DB engine, and disabled scheduler
- WebSocket tests: use `client.websocket_connect("/api/chat/ws")` and drain tokens until the `{"type": "end"}` JSON marker
- For direct DB assertions, use `Session(test_engine)` imported from `tests.conftest`

## Debug Mode

Enable verbose backend logging by setting the debug flag in your `.env`:

```
ASSISTANT_DEBUG=true
```

This controls:
- **Backend:** Sets log level to DEBUG with timestamped output. All loggers (`app.api.chat`, `app.api.conversations`, `app.services.scheduler`, etc.) inherit this level.
- **Frontend:** `log()`, `warn()`, `error()` from `src/utils/logger.ts` only output in dev mode (`npm run dev`). Production builds (`npm run build`) strip all `console.*` calls via terser.

For the **in-browser debug panel** (error log), toggle it via Settings → Developer → Debug mode. No restart needed.

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Tech Decisions](docs/TECH_DECISIONS.md)
