# Tech Decisions Log

## 2026-02-16 - Initial Scoping

### Frontend
- **React + TypeScript** - standard, good ecosystem
- **CSS Modules** - scoped styles, no Tailwind
- **UI Library** - TBD, will evaluate: Mantine, Ant Design, or Radix UI + custom styles
- **Dark mode by default**
- **Fixed dashboard layout** (not draggable widgets)

### Backend
- **FastAPI** - async Python, good for WebSocket + REST
- **uv** - fast Python package manager
- **SQLite** - simple, no separate DB server, sufficient for single-user
- **SQLModel or SQLAlchemy** - ORM for SQLite

### LLM
- **Google Gemini API** to start (user has credits)
- **Abstract provider interface** - must be swappable to OpenAI, Anthropic, local (Ollama) later
- **Tool-use / function-calling** pattern for agent capabilities

### Voice
- **STT: Whisper (local)** - free, runs on server
- **TTS: ElevenLabs** - quality voices, API-based
- **Both behind abstract interfaces** for future swapping

### Integrations
- **Google** - Calendar, Drive, Gmail, all features via dedicated account
- **GitHub** - Projects (kanban), repos, via dedicated account
- **Web browsing** - fetch + summarize URLs, search
- **File system** - sandboxed to `backend/data/` only

### Security
- **No web auth** - Tailscale network = trusted
- **Sandboxed file access** - hard boundary, no path traversal
- **API keys server-side only** - never exposed to frontend
- **Dedicated Google/GitHub accounts** - limited blast radius

### Deployment
- Single machine, home server
- Tailscale for remote access
- Specific port exposed on Tailscale network
