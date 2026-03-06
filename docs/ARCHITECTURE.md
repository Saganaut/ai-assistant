# AI Assistant - Architecture

## Overview

A self-hosted personal AI assistant with a mobile-friendly web dashboard. Deployed locally on a home server, accessed remotely via Tailscale.

## Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Frontend    | React + TypeScript, CSS Modules     |
| Backend     | FastAPI (Python), managed with uv   |
| Database    | SQLite                              |
| LLM         | Google Gemini API (swappable)       |
| STT         | Web Speech API (primary), Whisper (fallback) |
| TTS         | ElevenLabs API (swappable)          |
| Auth        | None (Tailscale network = trusted)  |
| Deployment  | Home server, single-machine         |

## Monorepo Structure

```
ai-assistant/
├── frontend/          # React + TypeScript app
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/       # Chat panel, voice button, CLI terminal (xterm.js)
│   │   │   ├── Dashboard/  # All dashboard widgets
│   │   │   │   ├── WorkoutWidget.tsx   # BWF RR tracker
│   │   │   │   ├── RoutineEditor.tsx   # Routine CRUD modal
│   │   │   │   ├── DraggableGrid.tsx   # Drag-and-drop widget grid
│   │   │   │   └── ...
│   │   │   └── Layout/     # Header, settings modal, error log modal
│   │   ├── contexts/
│   │   │   └── ModeContext.tsx   # Overview / Health / Work mode state
│   │   ├── services/  # API client, websocket helpers
│   │   ├── utils/
│   │   │   ├── logger.ts        # Dev-only console logger
│   │   │   └── errorLog.ts      # In-browser error capture
│   │   ├── styles/    # Global styles, CSS variables
│   │   └── types/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── backend/
│   ├── app/
│   │   ├── api/       # FastAPI route handlers
│   │   │   ├── chat.py
│   │   │   ├── claude_cli.py    # /claude and /gemini WebSocket endpoints
│   │   │   ├── cli_ws.py        # PTY ↔ WebSocket bridge (session registry)
│   │   │   ├── conversations.py
│   │   │   ├── files.py
│   │   │   ├── integrations.py
│   │   │   ├── notes.py
│   │   │   ├── voice.py
│   │   │   ├── workouts.py      # Workout routine + log CRUD
│   │   │   └── ...
│   │   ├── core/      # Config, dependencies, sandbox
│   │   │   ├── config.py
│   │   │   ├── sandbox.py    # File access sandboxing
│   │   │   └── database.py
│   │   ├── services/  # Business logic
│   │   │   ├── llm/          # LLM provider abstraction
│   │   │   │   ├── base.py   # Abstract interface
│   │   │   │   ├── gemini.py
│   │   │   │   └── local.py  # Future: local models
│   │   │   ├── voice/        # Voice provider abstraction
│   │   │   │   ├── stt.py    # Whisper (local)
│   │   │   │   └── tts.py    # ElevenLabs (swappable)
│   │   │   ├── integrations/
│   │   │   │   ├── google.py    # Calendar, Drive, Gmail
│   │   │   │   ├── github.py    # GitHub Projects, repos
│   │   │   │   ├── wordpress.py # WordPress posts, media (XML-RPC + REST)
│   │   │   │   └── browser.py   # Web browsing/research
│   │   │   ├── scheduler/
│   │   │   │   ├── scheduler.py  # Cron-based background scheduler
│   │   │   │   └── models.py     # ScheduledAction, ScheduledRun
│   │   │   ├── files.py         # Sandboxed file operations
│   │   │   └── agent.py         # Agent orchestration (tool use)
│   │   ├── models/    # SQLite models (SQLAlchemy/SQLModel)
│   │   └── main.py
│   ├── tests/         # pytest test suite
│   │   ├── conftest.py
│   │   ├── test_api_health.py
│   │   ├── test_api_conversations.py
│   │   └── test_websocket_chat.py
│   ├── data/          # Sandboxed folder for LLM file access
│   │   └── workouts/
│   │       ├── routines/        # Routine JSON files
│   │       └── YYYY-MM-DD.json  # Daily workout logs
│   ├── pyproject.toml
│   └── .python-version
├── shared/            # Shared types/contracts (if needed)
├── docs/
├── CLAUDE.md
└── .gitignore
```

## Key Design Decisions

### 1. LLM Provider Abstraction

All LLM interactions go through an abstract interface (`services/llm/base.py`). Providers (Gemini, OpenAI, local Ollama, etc.) implement this interface. Swapping providers = changing one config value.

### 2. Sandboxed File Access

The LLM can ONLY access files within `backend/data/`. All file operations are validated against this path. Path traversal is blocked at the service layer. This is a hard security boundary. Workout data is stored within the sandbox at `data/workouts/`.

### 3. Agent / Tool-Use Pattern

The AI assistant uses a tool-use pattern:
- User sends a message
- LLM decides which tools to call (file ops, Google Calendar, GitHub, web search, etc.)
- Backend executes tools within sandboxed boundaries
- Results are returned to LLM for final response

Tools available to the agent:
- `read_file`, `write_file`, `list_files` (sandboxed)
- `google_calendar_*` (list, create, update events)
- `google_drive_*` (list, upload, download, search)
- `google_gmail_*` (read, send, search)
- `github_projects_*` (list, create, update cards/issues)
- `github_repos_*` (list, search, read files)
- `web_search`, `web_browse` (fetch and summarize URLs)
- `wordpress_*` (list, create, update, delete posts; upload media)
- `save_bookmark` (save URL + summary to notes)
- `health_note` (append to health/fitness notes)

### 4. Voice Pipeline

```
[Push-to-Talk] → [Web Speech API (primary) / Whisper (fallback)] → [Text to LLM] → [LLM Response] → [ElevenLabs TTS] → [Audio Playback]
```

**STT** uses the browser's Web Speech API (`SpeechRecognition`) as the primary path — it's native, low-latency, and works on mobile (iOS Safari, Android Chrome) without a server round-trip. Whisper (local, via WebSocket) is the fallback for browsers that don't support Web Speech API (e.g., Firefox). The Web Speech API requires a secure context (HTTPS or localhost).

Both STT and TTS are behind abstract interfaces for easy swapping.

### 5. Dashboard Modes

The dashboard has three modes selected via Settings → Mode:

| Mode | Layout |
|------|--------|
| **Overview** | Draggable grid — all widgets (Markets, Calendar, Kanban, WordPress, Scheduler, Notes, Files) |
| **Work** | Draggable grid — Calendar, Kanban, Scheduler, Notes |
| **Health** | Fixed — Calendar + Notes as collapsible tabs (top), WorkoutWidget full-width (bottom) |

Mode is stored in `localStorage('app_mode')` and synced across tabs via the `storage` event. `ModeContext` (`src/contexts/ModeContext.tsx`) provides `mode` and `setMode` to the component tree.

```
┌────────────────────────────────────────────┐
│  Header  [AI Assistant · Health]  ⚙        │
├────────────────────────────────────────────┤
│  [Calendar | Notes]  ▴                     │  ← collapsible tab bar (Health mode)
│  ┌─────────────────────────────────────┐   │
│  │  CalendarWidget / QuickNotes        │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  WorkoutWidget (full-width)         │   │
│  └─────────────────────────────────────┘   │
│                           │  Chat Panel    │
└───────────────────────────┴────────────────┘
```

On mobile, the tab bar is always visible; the widget content is hidden when collapsed.

### 6. CLI Terminal (PTY ↔ WebSocket Bridge)

Typing `/claude` or `/gemini` in chat opens an embedded xterm.js terminal that connects to the backend over WebSocket. The backend spawns the CLI in a pseudo-terminal (PTY).

**Session persistence** is the critical design requirement — the user navigates between views and the process must not be killed.

```
Frontend (xterm.js)              Backend
────────────────────             ────────────────────────────────────────
connectCliWs(mode, sessionId)    run_cli_over_ws(websocket, command)
  │                                │
  │──── WS connect ───────────────→│  Resume existing session or spawn new PTY
  │←─── cli_ready {session_id} ───│  Send session_id so client can reconnect
  │                                │
  │  [user types]                  │
  │──── raw bytes ────────────────→│  os.write(master_fd, data)
  │←─── PTY output ───────────────│  os.read(master_fd) in _pty_reader task
  │                                │
  │  [user navigates away]         │
  │──── WS close ─────────────────→│  ws_holder[0] = None  (PTY reader keeps running,
  │                                │   discards output; 60s cleanup timer starts)
  │  [user returns within 60s]     │
  │──── WS connect + session_id ──→│  Cancel cleanup; ws_holder[0] = new_ws; resumed=true
  │←─── cli_ready {resumed:true} ─│
  │←─── PTY output (resumes) ─────│
```

Key implementation details:
- `_sessions: dict[str, PtySession]` — module-level registry, one entry per live session
- `ws_holder: list[WebSocket | None]` — a mutable one-element list shared between the session and its reader coroutine; avoids closure issues with reassignment
- `_pty_reader` — one long-running asyncio task per session; reads from the PTY master fd, writes to whatever WebSocket is currently in `ws_holder[0]`
- Deferred cleanup — on WS disconnect, a `_deferred_cleanup` task sleeps 60 s then terminates the process; cancelled on reconnect
- xterm.js — `convertEol: false` (PTY handles line endings); `TERM=xterm-256color`; `requestAnimationFrame` before `fitAddon.fit()` to ensure DOM is laid out; resize message forwarded to PTY via `TIOCSWINSZ`
- Scrollbar — xterm's internal `.xterm-viewport` scrollbar is hidden via CSS (width 0) to eliminate phantom right-side padding

### 7. Workout Tracker

The WorkoutWidget implements the BWF Recommended Routine. Key design choices:

**Data flow:**
```
Backend JSON files          Frontend
────────────────────        ──────────────────────────────
/api/workouts/routines  →   WorkoutWidget loads routines on mount
/api/workouts/logs      →   loadTodayLog: check localStorage draft first,
                              then fetch from API
                        ←   saveWorkoutLog: POST to API + update localStorage
```

**Draft persistence** — workout state is auto-saved to `localStorage` on every change (`useEffect([log])`). The draft includes `{ savedAt, log }`. On load, the draft is used if:
1. It exists for the selected routine
2. `date === today` (drafts don't carry over to the next day)
3. Age < 3 hours (`DRAFT_TTL = 3 * 60 * 60 * 1000`)

**Routine storage** — each routine is stored as a JSON file in `backend/data/workouts/routines/{id}.json`. The BWF RR is seeded on the first `GET /api/workouts/routines` request if no routines exist.

### 8. In-Browser Error Capture

`src/utils/errorLog.ts` captures errors without interfering with the rest of the app:
- Monkey-patches `console.error`
- Listens to `window.addEventListener('unhandledrejection')` and `window.addEventListener('error')`
- Stores entries in a circular buffer (max 100)
- Uses an **immutable snapshot pattern** for `useSyncExternalStore` compatibility: `snapshot` is replaced with a new array reference on every mutation; `getEntries()` returns the same reference between mutations (required — React uses `Object.is` to detect changes)

The error log button in the header is only visible when debug mode is enabled (Settings → Developer → Debug mode). Debug mode is stored in `localStorage('debug_mode')`.

### 9. No Auth

Tailscale network membership = authorization. No login screen, no tokens for the web UI. API keys for external services (Gemini, ElevenLabs, Google, GitHub, WordPress) are stored server-side in environment variables.

### 10. Networking & Tailscale Serve

The frontend uses relative URLs (`/api/...`) for all API and WebSocket calls — no hardcoded ports or hostnames. This works in two modes:

**Local development** — Vite's dev proxy (`vite.config.ts`) forwards `/api` requests to `http://localhost:8000`:
```bash
cd frontend && npm run dev    # serves UI on :5173, proxies /api → :8000
cd backend && uv run uvicorn app.main:app --reload  # serves API on :8000
```

**Tailscale HTTPS (mobile / remote access)** — Use `tailscale serve` to expose both frontend and backend on a single HTTPS origin. This is required for features that need a secure context (Web Speech API, microphone access):
```bash
tailscale serve --https=443 / http://localhost:5173
tailscale serve --https=443 /api http://localhost:8000/api
```
Then access via `https://<machine>.<tailnet>.ts.net`.

The API base URL can be overridden with the `VITE_API_BASE` env var if needed (e.g., `VITE_API_BASE=http://192.168.1.50:8000/api`). The WebSocket base URL is derived from the same value automatically.

### 11. Scheduled Actions (Automation)

The assistant can run tasks autonomously on a schedule, not just on-demand.

**Architecture:**
- A `Scheduler` service runs in the backend as a background task on app startup
- Schedules are stored in SQLite (`scheduled_actions` table)
- Each schedule defines: a cron expression, a prompt/instruction for the LLM, and which tools it's allowed to use
- When a schedule fires, the scheduler invokes the agent with the stored prompt, just like a user message but flagged as `source: scheduled`
- Results are saved to the conversation history and optionally written to a file in the sandbox

**Safety:**
- All scheduled actions run through the same sandbox and tool permissions as on-demand requests
- Rate limiting: max N scheduled runs per hour to prevent runaway loops
- Failed runs are logged and retried with backoff (max 3 retries)

```
┌─────────────┐     cron fires      ┌──────────────┐
│  Scheduler  │ ──────────────────→  │    Agent     │
│  (APScheduler│                     │  (same as    │
│   or custom) │                     │   chat agent)│
└─────────────┘                      └──────┬───────┘
                                            │
                                     uses tools, writes results
                                            │
                                     ┌──────▼───────┐
                                     │   SQLite     │
                                     │  (run log)   │
                                     └──────────────┘
```

## Logging

### Backend
Centralized logging is configured in `app/main.py` during the lifespan startup, controlled by `settings.debug`:
- **Debug mode** (`ASSISTANT_DEBUG=true`): DEBUG level, verbose format with timestamps
- **Production** (default): INFO level, concise format

All modules use `logging.getLogger(__name__)` so they inherit the root config. Key loggers: `app.api.chat` (WebSocket events, agent errors), `app.api.conversations` (CRUD operations), `app.services.scheduler` (scheduled runs), `app.api.cli_ws` (PTY session lifecycle).

### Frontend
`src/utils/logger.ts` exports `log`, `warn`, `error` functions guarded by `import.meta.env.DEV`. In dev mode they output to the console; in production builds Vite tree-shakes them away. The Vite build also uses terser to strip any remaining `console.*` calls and comments.

The in-browser debug panel (`src/utils/errorLog.ts`) is separate from the logger — it captures errors at runtime in production without any build-time stripping, gated only by the debug mode setting.

## Testing

Backend tests use pytest with pytest-asyncio. All tests run against an in-memory SQLite database that resets per test.

Key fixtures (in `tests/conftest.py`):
- `setup_test_db` (autouse) — creates/drops tables each test
- `mock_agent` — async generator yielding fake tokens
- `client` — FastAPI `TestClient` with patched DB engine, mocked agent, and disabled scheduler

Test coverage: health endpoint, conversation CRUD + 404s, WebSocket chat (streaming, persistence, multi-turn conversations).

```bash
cd backend && uv run pytest tests/ -v
```

## Communication

- REST API for most operations
- WebSocket for chat streaming, voice audio, and CLI PTY sessions
