# AI Assistant - Roadmap

## v0.1 - Foundation

**Goal:** Basic scaffolding, chat working, file access.

- [ ] Project scaffolding (frontend + backend)
- [ ] FastAPI app with health check
- [ ] React app with dark mode, CSS Modules, basic layout shell
- [ ] SQLite database setup (conversation history)
- [ ] LLM provider abstraction + Gemini implementation
- [ ] Basic chat UI (text only, no tools)
- [ ] Chat streaming via WebSocket
- [ ] Sandboxed local file access (read/write/list)
- [ ] File browser widget in dashboard

## v0.2 - Agent & Tools

**Goal:** AI can use tools, not just chat.

- [ ] Tool-use / function-calling framework
- [ ] Agent orchestration (multi-step tool use)
- [ ] File tools (read, write, list, search within sandbox)
- [ ] Web browsing tool (fetch URL, summarize, save bookmark)
- [ ] Web search tool
- [ ] Health/fitness note tool
- [ ] Dashboard: quick notes widget

## v0.3 - Google Integration

**Goal:** Calendar, Drive, Gmail connected.

- [ ] Google OAuth setup (dedicated service account)
- [ ] Google Calendar tools (list, create, update, delete events)
- [ ] Google Drive tools (list, upload, download, search)
- [ ] Google Gmail tools (read, send, search)
- [ ] Dashboard: calendar widget (today/week view)

## v0.4 - GitHub Integration

**Goal:** GitHub Projects and repos accessible.

- [ ] GitHub CLI / API integration (dedicated account)
- [ ] GitHub Projects tools (list, create, move cards)
- [ ] GitHub repos tools (list, search, read files)
- [ ] Dashboard: kanban widget

## v0.5 - Voice

**Goal:** Push-to-talk voice interaction.

- [ ] Whisper STT (local) integration
- [ ] ElevenLabs TTS integration
- [ ] TTS/STT provider abstraction
- [ ] Push-to-talk UI component
- [ ] Audio streaming via WebSocket
- [ ] Voice activity in chat history

## v0.6 - Scheduled Actions

**Goal:** AI can act autonomously on a schedule.

- [ ] Scheduler service (background task, cron-based)
- [ ] `scheduled_actions` SQLite table (cron, prompt, tool permissions, enabled)
- [ ] `scheduled_runs` SQLite table (run log with timestamps, results, status)
- [ ] REST API for schedule CRUD (`/api/schedules`)
- [ ] Scheduled runs go through same agent/tool pipeline as chat
- [ ] Rate limiting and retry logic (max 3 retries with backoff)
- [ ] Dashboard: scheduled actions widget (upcoming, recent runs, enable/disable)
- [ ] Built-in templates: morning briefing, daily summary, inbox triage

## v0.7 - Polish & Mobile

**Goal:** Mobile-friendly, responsive, smooth UX.

- [ ] Responsive layout (stacked on mobile)
- [ ] Floating chat button on mobile
- [ ] Touch-friendly push-to-talk
- [ ] Conversation history persistence + search
- [ ] Settings page (API keys, preferences)
- [ ] Error handling and loading states

## Future Ideas

- Habit tracker widget
- Budget/finance tracking
- Smart home integration (Home Assistant API)
- Local LLM support (Ollama)
- Local TTS (Piper, Coqui)
- RAG over uploaded documents
- Notifications (push notifications via Tailscale)
