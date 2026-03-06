# Tech Decisions Log

## 2026-02-27 - CLI Terminal (PTY Session Persistence)

### Why PTY over raw subprocess
A pseudo-terminal (PTY) is required because `claude` and `gemini` CLIs detect whether they are running interactively (via `isatty()`). Without a PTY they switch to non-interactive modes, disable color/ANSI output, and behave differently. `pty.openpty()` gives us a master/slave fd pair; the slave is passed as stdin/stdout/stderr to `asyncio.create_subprocess_exec`, which satisfies the TTY check.

### Session persistence with `ws_holder`
The key problem: WebSocket disconnects are transient (navigation, screen lock, brief network drop) but the PTY process is long-lived. Killing it on every disconnect would lose all state.

Design: one `_pty_reader` asyncio task per session runs for the entire lifetime of the process. The reader writes to `ws_holder[0]` — a mutable one-element list shared by reference. When the WebSocket disconnects, we set `ws_holder[0] = None`; the reader keeps running and discards output. On reconnect we set `ws_holder[0] = new_ws` and cancel the deferred cleanup task.

Why a list instead of a plain variable? Python closures capture variables by reference to the enclosing scope's name binding. If we did `ws = new_ws` in the reconnect path, the reader's closure would still see the old `ws`. A mutable container (`ws_holder: list[WebSocket | None] = [None]`) lets both sides share the same object.

### Session timeout
60 seconds (`SESSION_TIMEOUT`). Long enough to survive navigation or a brief screen lock; short enough not to leave zombie processes indefinitely. Configurable at the top of `cli_ws.py`.

### xterm.js sizing
- Initial PTY size: 50 rows × 220 cols (generous). This prevents the first render being squished before the client has a chance to measure its container and send real dimensions.
- `fitAddon.fit()` is called inside `requestAnimationFrame` to ensure the DOM is fully laid out before measuring the terminal container size. Without `rAF`, the container may still have zero dimensions.
- After fit, the client sends a `{"type":"resize","rows":R,"cols":C}` message; the backend calls `fcntl.ioctl(fd, termios.TIOCSWINSZ, ...)`.
- `TERM=xterm-256color`, `COLORTERM=truecolor` are set in the subprocess environment so the CLIs enable full color output.

### Scrollbar padding
xterm.js renders an internal scrollbar inside `.xterm-viewport`. Even when content fits on screen, the browser reserves space for it, appearing as blank padding on the right. Fixed with CSS:
```css
.terminalOutput :global(.xterm-viewport) { scrollbar-width: none; }
.terminalOutput :global(.xterm-viewport)::-webkit-scrollbar { width: 0; }
```

### Reconnect strategy (frontend)
- `cliSessionIdRef` — stores the `session_id` received in the `cli_ready` message
- On unexpected close: exponential backoff (1 s, 2 s, 4 s… max 30 s), max 10 attempts
- ANSI escape sequences used for status messages inside the terminal (`\x1b[33m...\x1b[0m` for yellow)
- `cliIntentionalCloseRef` distinguishes user-initiated close (type `/exit`) from unexpected disconnect

---

## 2026-02-27 - Dashboard Modes & ModeContext

### Why three modes
The dashboard was accumulating widgets for different contexts (work, fitness, general overview). Rather than a settings screen with checkboxes, fixed modes give each context a clean, purpose-built layout. New modes can be added without changing the core layout engine.

### ModeContext implementation
- `localStorage('app_mode')` for persistence; read once at init, no re-reads
- `storage` event listener for cross-tab sync (editing settings in one tab reflects in others)
- Context value: `{ mode, setMode }` — `setMode` writes to both React state and localStorage atomically

### Health mode layout
Calendar and Notes share a tab bar rather than sitting side-by-side. On narrow screens, two widgets at `1fr 1fr` overflow. Tabs eliminate the overflow entirely — only one widget is visible at a time. The tab container is also collapsible (▴/▾) so the full viewport can be given to the workout tracker.

---

## 2026-02-27 - Workout Tracker

### Routine storage (JSON files, not SQLite)
Routines are structured but user-editable data that benefits from being human-readable on disk. JSON files in `backend/data/workouts/routines/{id}.json` fit the existing sandboxed file pattern and are easy to inspect/edit manually. SQLite would add a schema migration concern for a single-user app with infrequent writes.

### Progression numbering (0-indexed)
Progressions within each exercise are displayed as "L0", "L1", "L2"… in the UI and stored as `progressionLevel` (integer index) in the workout log. This lets the backend remain agnostic about progression names — the UI looks up the name from the routine definition at render time.

### Draft persistence
Workout sessions can last up to ~1 hour; mobile browsers may suspend the page (screen lock, app switch). Without persistence, in-progress data would be lost. `localStorage` is the right tool: synchronous, always available, no server round-trip.

Draft structure: `{ savedAt: number, log: WorkoutLog }`. On load:
1. Try to load draft from `localStorage(DRAFT_KEY)`
2. Reject if: no draft, wrong `routineId`, `date !== today`, or age > 3 h
3. Otherwise use draft; still show a "saved draft" indicator
4. On explicit save (POST to API), the draft is not cleared — it remains as a local cache

---

## 2026-02-27 - In-Browser Error Capture & useSyncExternalStore

### Why capture errors in-browser
Development happens on a mobile device over Tailscale. Opening DevTools on mobile is cumbersome. A live error log in the UI — gated by a debug mode toggle — gives immediate visibility into console errors and unhandled rejections without needing a laptop.

### Immutable snapshot pattern for useSyncExternalStore
`useSyncExternalStore(subscribe, getSnapshot)` calls `getSnapshot` after every render and compares the result with `Object.is`. If the reference changes, React re-renders — then calls `getSnapshot` again — creating an infinite loop.

**Wrong:**
```ts
// New array every call → Object.is always false → infinite loop
const entries = useSyncExternalStore(subscribe, () => [...getEntries()]);
```

**Right:**
```ts
// snapshot is replaced (new reference) only on push/clear
let snapshot: readonly ErrorEntry[] = [];
function push(entry) { snapshot = [...snapshot, newEntry]; notify(); }
function getEntries() { return snapshot; } // stable between mutations

const entries = useSyncExternalStore(subscribe, getEntries, getEntries);
```

React's console warning `"The result of getSnapshot should be cached to avoid an infinite loop"` points directly at this pattern.

---

## 2026-02-18 - WordPress Integration

### Authentication
- **XML-RPC for all authenticated writes** — The user's Apache server strips the `Authorization` header before PHP sees it (`rest_not_logged_in`). HTTP Basic auth (Application Passwords) is silently rejected. XML-RPC puts credentials in the XML request body, bypassing header stripping entirely.
- **REST API only for public reads** — Published posts, categories, and tags are publicly accessible via the REST API without auth.
- `wordpress.py` uses `xmlrpc.client.ServerProxy` wrapped in `asyncio.to_thread` for async compatibility.

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

---

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

---

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

---

## 2026-02-16 - Initial Scoping

### Frontend
- **React + TypeScript** - standard, good ecosystem
- **CSS Modules** - scoped styles, no Tailwind
- **Dark mode by default**

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
