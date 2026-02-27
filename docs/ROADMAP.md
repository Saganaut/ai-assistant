# AI Assistant - Roadmap

## v0.1 - Foundation

**Goal:** Basic scaffolding, chat working, file access.

- [x] Project scaffolding (frontend + backend)
- [x] FastAPI app with health check
- [x] React app with dark mode, CSS Modules, basic layout shell
- [x] SQLite database setup (conversation history)
- [x] LLM provider abstraction + Gemini implementation
- [x] Basic chat UI (text only, no tools)
- [x] Chat streaming via WebSocket
- [x] Sandboxed local file access (read/write/list)
- [x] File browser widget in dashboard

## v0.2 - Agent & Tools

**Goal:** AI can use tools, not just chat.

- [x] Tool-use / function-calling framework
- [x] Agent orchestration (multi-step tool use)
- [x] File tools (read, write, list, search within sandbox)
- [x] Web browsing tool (fetch URL, summarize, save bookmark)
- [x] Web search tool
- [x] Health/fitness note tool
- [x] Dashboard: quick notes widget

## v0.3 - Google Integration

**Goal:** Calendar, Drive, Gmail connected.

- [x] Google OAuth setup (dedicated service account)
- [x] Google Calendar tools (list, create, update, delete events)
- [x] Google Drive tools (list, upload, download, search)
- [x] Google Gmail tools (read, send, search)
- [x] Dashboard: calendar widget (today/week view)

## v0.4 - GitHub Integration

**Goal:** GitHub Projects and repos accessible.

- [x] GitHub CLI / API integration (dedicated account)
- [x] GitHub Projects tools (list, create, move cards)
- [x] GitHub repos tools (list, search, read files)
- [x] Dashboard: kanban widget

## v0.5 - Voice

**Goal:** Push-to-talk voice interaction.

- [x] Whisper STT (local) integration
- [x] ElevenLabs TTS integration
- [x] TTS/STT provider abstraction
- [x] Push-to-talk UI component
- [x] Audio streaming via WebSocket
- [x] Voice activity in chat history

## v0.6 - Scheduled Actions

**Goal:** AI can act autonomously on a schedule.

- [x] Scheduler service (background task, cron-based)
- [x] `scheduled_actions` SQLite table (cron, prompt, tool permissions, enabled)
- [x] `scheduled_runs` SQLite table (run log with timestamps, results, status)
- [x] REST API for schedule CRUD (`/api/schedules`)
- [x] Scheduled runs go through same agent/tool pipeline as chat
- [x] Rate limiting and retry logic (max 3 retries with backoff)
- [x] Dashboard: scheduled actions widget (upcoming, recent runs, enable/disable)
- [x] Built-in templates: morning briefing, daily summary, inbox triage

## v0.7 - Polish & Mobile

**Goal:** Mobile-friendly, responsive, smooth UX.

- [x] Responsive layout (stacked on mobile)
- [x] Floating chat button on mobile
- [x] Touch-friendly push-to-talk
- [x] Conversation history persistence + search
- [x] Settings page (API keys, preferences)
- [x] Error handling and loading states

## v0.8 - Testing & Observability

**Goal:** Backend test suite, structured logging, frontend log utility, clean production builds.

- [x] pytest + pytest-asyncio setup with in-memory SQLite
- [x] Test fixtures: mock agent, patched DB engine, disabled scheduler
- [x] WebSocket chat tests (streaming, persistence, multi-turn)
- [x] REST API tests (health, conversations CRUD, 404 handling)
- [x] Centralized backend logging config (DEBUG/INFO keyed off `settings.debug`)
- [x] Error logging + WebSocket error messages in chat handler
- [x] Frontend logger utility (`src/utils/logger.ts`) — dev-only, tree-shaken in prod
- [x] Vite production build: terser minification, console stripping, comment removal

## v0.9 - WordPress Integration

**Goal:** Manage WordPress blog directly from the dashboard.

- [x] WordPress REST API service (Application Passwords auth)
- [x] List/view posts with status filtering (publish, draft, pending)
- [x] Create new posts with title, content, tags, categories
- [x] Publish drafts from detail view
- [x] Image upload with automatic WebP conversion and resize (<100KB)
- [x] Featured image support on new posts
- [x] Compose view in dashboard widget (mobile-friendly)
- [x] Agent tools: `wordpress_list_posts`, `wordpress_create_post`, `wordpress_upload_media`
- [x] Update and delete posts via API

## Future Ideas

- Habit tracker widget
- Budget/finance tracking
- Smart home integration (Home Assistant API)
- Local LLM support (Ollama)
- Local TTS (Piper, Coqui)
- RAG over uploaded documents
- Notifications (push notifications via Tailscale)
