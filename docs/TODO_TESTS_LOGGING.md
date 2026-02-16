# Plan: Backend Tests, Logging, and Frontend Build Config

## Context
The project has no tests, inconsistent backend logging, no frontend logging utility, and the Vite build doesn't strip comments. The WebSocket connection keeps dying silently with no useful error info. We need tests (especially WebSocket), better error visibility, and a clean production build.

---

## 1. Backend Tests

### Setup
- **`backend/pyproject.toml`** — Add `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` and `testpaths = ["tests"]`
- **`backend/tests/__init__.py`** — Empty
- **`backend/tests/conftest.py`** — Core fixtures:
  - In-memory SQLite test engine
  - `setup_test_db` fixture (autouse) — creates/drops tables per test
  - `mock_agent` fixture — async generator yielding fake tokens
  - `client` fixture — FastAPI TestClient with patches for: `engine` (in both `database` and `chat` modules), `Agent`, `get_session`, `scheduler_loop`

### Test Files
- **`backend/tests/test_websocket_chat.py`** (primary focus):
  - Connection/disconnection
  - Send message → receive streamed tokens + end marker
  - JSON payload with conversation_id
  - Messages persisted to DB (user + assistant)
  - Multiple messages reuse same conversation
  - Agent error → graceful handling (documents current gap)
  - Load existing conversation history

- **`backend/tests/test_api_health.py`**: Health endpoint returns 200

- **`backend/tests/test_api_conversations.py`**: List, get, delete conversations; 404 handling

### Key patching strategy
- `app.core.database.engine` AND `app.api.chat.engine` (Python `from X import Y` creates separate binding)
- `app.api.conversations.get_session` → test session generator
- `app.api.chat.Agent` → mock that yields fake tokens
- `app.services.scheduler.scheduler.scheduler_loop` → noop coroutine

---

## 2. Backend Logging & Debug Mode

### Centralized logging config in `backend/app/main.py`
- Add `logging.basicConfig()` call in the lifespan, keyed off `settings.debug`:
  - `debug=True` → level DEBUG, verbose format with timestamps
  - `debug=False` → level INFO, concise format
- Sets root logger so all `logging.getLogger(__name__)` calls pick it up

### Add error logging to `backend/app/api/chat.py`
- Add `logger = logging.getLogger(__name__)`
- Wrap `agent.run()` loop in try/except — log the error AND send an error message to the WebSocket client before closing
- Log WebSocket connect/disconnect events
- Log conversation creation

### Add logging to `backend/app/api/conversations.py`
- Log delete operations and 404s at DEBUG level

---

## 3. Frontend Logging Utility

### `frontend/src/utils/logger.ts`
- Export `log`, `warn`, `error` functions that wrap `console.*`
- Guard with `import.meta.env.DEV` — in production builds, Vite statically replaces this with `false` and tree-shaking removes the dead code
- No runtime cost in production

### Update existing code
- Replace `console.error` in `VoiceButton.tsx` with `logger.error`
- Add logging to `Chat.tsx` WebSocket events (connect, disconnect, reconnect attempts, errors)

---

## 4. Vite Production Build Config

### `frontend/vite.config.ts`
- Add `build.minify: 'terser'` with terserOptions:
  - `compress.drop_console: true` — strips any remaining console.* calls
  - `format.comments: false` — removes all comments from output

---

## Files to Create
- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/test_websocket_chat.py`
- `backend/tests/test_api_health.py`
- `backend/tests/test_api_conversations.py`
- `frontend/src/utils/logger.ts`

## Files to Modify
- `backend/pyproject.toml` — pytest config
- `backend/app/main.py` — logging.basicConfig
- `backend/app/api/chat.py` — error handling + logging
- `backend/app/api/conversations.py` — logging
- `frontend/vite.config.ts` — terser + comment stripping
- `frontend/src/components/Chat/Chat.tsx` — use logger
- `frontend/src/components/Chat/VoiceButton.tsx` — use logger

## Verification
```bash
# Backend tests
cd backend && uv run pytest tests/ -v

# Frontend build (verify no console/comments in output)
cd frontend && npm run build && grep -r "console\." dist/ | head
```
