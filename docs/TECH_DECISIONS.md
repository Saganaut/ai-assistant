# Tech Decisions Log

## 2026-02-18 - WordPress Integration

### Authentication
- **Application Passwords** — WordPress's built-in auth method (WP 5.6+). No plugins needed. Generate via WP Admin → Users → Edit User → Application Passwords. Sent as HTTP Basic auth (`base64(username:app_password)`).
- Simpler than OAuth, sufficient for single-user self-hosted setup.

### Image Processing
- **Pillow for WebP conversion** — all uploaded images are converted to WebP and iteratively resized until under 100KB. This keeps media storage small and page loads fast.
- Process: open image → convert to RGB (strip alpha) → save as WebP at quality 80 → if >100KB, resize to 75% dimensions and repeat (up to 10 rounds).

### REST API Workarounds
- **Single status per request** — WordPress REST API's `GET /posts` only accepts one `status` value. To show "all" posts, we fetch `publish`, `draft`, and `pending` separately and merge client-side, sorted by date.

### Setup
To enable WordPress integration:
1. Go to WP Admin → Users → Edit your user → Application Passwords
2. Create a new application password (name it anything, e.g., "AI Assistant")
3. Set environment variables:
   - `ASSISTANT_WORDPRESS_URL` — your WordPress site URL (e.g., `https://example.com`)
   - `ASSISTANT_WORDPRESS_USERNAME` — your WordPress username
   - `ASSISTANT_WORDPRESS_APP_PASSWORD` — the generated application password

## 2026-02-18 - Web Speech API for STT, Centralized API Base URL

### STT
- **Web Speech API as primary STT** — native browser API, works on iOS Safari and Android Chrome with no server round-trip. Low latency, free, on-device.
- **Whisper as fallback** — used only when `SpeechRecognition` is unavailable (e.g., Firefox). Existing MediaRecorder + WebSocket flow unchanged.
- **Secure context required** — Web Speech API and `getUserMedia` both need HTTPS or localhost. Over plain HTTP (e.g., Tailscale without HTTPS), neither STT path works on mobile. Detection uses `window.isSecureContext` to avoid silent failures.
- **Type declarations** — Added `frontend/src/types/speech-recognition.d.ts` since TypeScript's DOM lib doesn't include Web Speech API types.

### Networking
- **Removed all hardcoded `:8000` URLs** from frontend. All API/WebSocket calls now use relative paths (`/api/...`), derived from a single `API_BASE` in `services/api.ts`.
- **Vite dev proxy** added — `/api` requests are proxied to `http://localhost:8000` during development, so the frontend and backend share the same origin.
- **Tailscale Serve** for HTTPS — `tailscale serve` maps `/` to the frontend and `/api` to the backend on one HTTPS origin. This is the recommended way to access the app from mobile.
- **`VITE_API_BASE` env var** — optional override if the backend is hosted at a different origin.

## 2026-02-18 - Testing, Logging & Build Config

### Testing
- **pytest + pytest-asyncio** — standard Python async test stack
- **In-memory SQLite** for test DB — fast, isolated, no cleanup needed
- **Patching strategy:** Python's `from X import Y` creates separate bindings, so we patch both `app.core.database.engine` and `app.api.chat.engine` (and similar for other modules that import at module level)
- **Mock agent** yields fake tokens as an async generator — tests WebSocket streaming without hitting any LLM API
- **Scheduler disabled** in tests via patching `scheduler_loop` with a noop coroutine

### Logging
- **Backend:** `logging.basicConfig()` in lifespan startup, keyed off `settings.debug`. All modules use `logging.getLogger(__name__)` to inherit root config. No per-module config needed.
- **Frontend:** Dev-only logger utility guarded by `import.meta.env.DEV` — Vite statically replaces this at build time, and tree-shaking removes the dead code. Zero runtime cost in production.

### Build
- **Vite + terser** for production builds — `drop_console: true` strips console calls, `comments: false` removes comments. Belt-and-suspenders with the logger utility's dev guard.

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
