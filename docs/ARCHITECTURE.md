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
| STT         | Whisper (local)                     |
| TTS         | ElevenLabs API (swappable)          |
| Auth        | None (Tailscale network = trusted)  |
| Deployment  | Home server, single-machine         |

## Monorepo Structure

```
ai-assistant/
├── frontend/          # React + TypeScript app
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/  # API client, websocket
│   │   ├── styles/    # Global styles, CSS variables
│   │   └── types/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── backend/
│   ├── app/
│   │   ├── api/       # FastAPI route handlers
│   │   │   ├── chat.py
│   │   │   ├── files.py
│   │   │   ├── dashboard.py
│   │   │   └── voice.py
│   │   ├── core/      # Config, dependencies, security
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
│   │   │   │   ├── google.py    # Calendar, Drive, Gmail, etc.
│   │   │   │   ├── github.py    # GitHub Projects, repos
│   │   │   │   └── browser.py   # Web browsing/research
│   │   │   ├── scheduler/
│   │   │   │   ├── scheduler.py  # Cron-based background scheduler
│   │   │   │   └── models.py     # ScheduledAction, ScheduledRun
│   │   │   ├── files.py         # Sandboxed file operations
│   │   │   └── agent.py         # Agent orchestration (tool use)
│   │   ├── models/    # SQLite models (SQLAlchemy/SQLModel)
│   │   └── main.py
│   ├── data/          # Sandboxed folder for LLM file access
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

The LLM can ONLY access files within `backend/data/`. All file operations are validated against this path. Path traversal is blocked at the service layer. This is a hard security boundary.

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
- `save_bookmark` (save URL + summary to notes)
- `health_note` (append to health/fitness notes)

### 4. Voice Pipeline

```
[Push-to-Talk] → [Whisper STT (local)] → [Text to LLM] → [LLM Response] → [ElevenLabs TTS] → [Audio Playback]
```

Both STT and TTS are behind abstract interfaces for easy swapping.

### 5. Dashboard Layout (Fixed)

```
┌─────────────────────────────────────────┐
│  Header / Status Bar                     │
├──────────────────┬──────────────────────┤
│                  │                      │
│  Kanban /        │   Chat Panel         │
│  Projects        │   (with voice)       │
│                  │                      │
├──────────────────┤                      │
│                  │                      │
│  Calendar        │                      │
│  (Today/Week)    │                      │
│                  │                      │
├──────────────────┤                      │
│  Quick Notes     │                      │
│  / Health Log    │                      │
│                  ├──────────────────────┤
│                  │  File Browser        │
│                  │  (sandboxed)         │
└──────────────────┴──────────────────────┘
```

On mobile, these stack vertically with the chat panel accessible via a floating button.

### 6. No Auth

Tailscale network membership = authorization. No login screen, no tokens for the web UI. API keys for external services (Gemini, ElevenLabs, Google, GitHub) are stored server-side in environment variables.

### 7. Scheduled Actions (Automation)

The assistant can run tasks autonomously on a schedule, not just on-demand.

**Architecture:**
- A `Scheduler` service runs in the backend as a background task on app startup
- Schedules are stored in SQLite (`scheduled_actions` table)
- Each schedule defines: a cron expression, a prompt/instruction for the LLM, and which tools it's allowed to use
- When a schedule fires, the scheduler invokes the agent with the stored prompt, just like a user message but flagged as `source: scheduled`
- Results are saved to the conversation history and optionally written to a file in the sandbox

**Example scheduled actions:**
- **Morning briefing** (daily 7am): "Summarize today's calendar, list open GitHub issues assigned to me, check unread emails"
- **Daily summary** (daily 10pm): "Write a summary of what happened today to notes/daily/YYYY-MM-DD.md"
- **Inbox triage** (every 2 hours): "Check for new emails, flag anything urgent"
- **Health reminder** (daily 8pm): "Ask me to log today's health notes" (queues a notification/prompt)
- **Project sync** (daily 9am): "Check GitHub Projects for stale cards, summarize blockers"

**Management:**
- Schedules are CRUD-managed via REST API (`/api/schedules`)
- UI: a "Scheduled Actions" widget on the dashboard showing upcoming/recent runs
- Each run is logged with: timestamp, prompt, result, success/failure
- Schedules can be enabled/disabled without deleting them

**Safety:**
- All scheduled actions run through the same sandbox and tool permissions as on-demand requests
- A schedule cannot escalate its own permissions
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

## Communication

- REST API for most operations
- WebSocket for chat streaming and voice audio
