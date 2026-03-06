"""
PTY ↔ WebSocket bridge with session persistence.

Each CLI session owns a long-running PTY reader task.  The reader forwards
output to whatever WebSocket is currently attached (ws_holder[0]).  When the
WebSocket disconnects, the reader keeps running and discards output.  If a
client reconnects within SESSION_TIMEOUT seconds, it re-attaches and the
process continues.  After the timeout the process is terminated.
"""

import asyncio
import fcntl
import json
import logging
import os
import pty
import struct
import termios
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

SESSION_TIMEOUT = 60  # seconds to keep a disconnected session alive


def _set_pty_size(fd: int, rows: int, cols: int) -> None:
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


@dataclass
class PtySession:
    session_id: str
    command: str
    master_fd: int
    process: asyncio.subprocess.Process
    # Mutable one-element list so the pty_reader coroutine can see WS changes
    ws_holder: list = field(default_factory=lambda: [None])
    read_task: asyncio.Task | None = None
    cleanup_task: asyncio.Task | None = None

    def cancel_cleanup(self) -> None:
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            self.cleanup_task = None

    async def terminate(self) -> None:
        self.cancel_cleanup()
        if self.read_task and not self.read_task.done():
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
        try:
            os.close(self.master_fd)
        except OSError:
            pass
        if self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except (ProcessLookupError, asyncio.TimeoutError):
                try:
                    self.process.kill()
                except ProcessLookupError:
                    pass


_sessions: dict[str, PtySession] = {}


async def run_cli_over_ws(
    websocket: WebSocket,
    command: str,
    args: list[str] | None = None,
    session_id: str | None = None,
):
    """Attach a WebSocket to a PTY session (resuming if session_id is known)."""
    await websocket.accept()

    session: PtySession | None = None
    resumed = False

    # ── Resume existing session ───────────────────────────────────────────────
    if session_id and session_id in _sessions:
        existing = _sessions[session_id]
        if existing.process.returncode is None:
            existing.cancel_cleanup()
            session = existing
            resumed = True
            logger.info("[%s] Resumed session %s", command, session_id)
        else:
            # Stale entry — process already exited
            _sessions.pop(session_id, None)

    # ── Create new session ────────────────────────────────────────────────────
    if session is None:
        session_id = str(uuid.uuid4())
        master_fd, slave_fd = pty.openpty()

        # Generous initial size so the first render isn't squished.
        # The client sends its real dimensions once the terminal is fitted.
        _set_pty_size(master_fd, 50, 220)

        env = {
            **os.environ,
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
        }
        cmd = [command] + (args or [])
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
            env=env,
        )
        os.close(slave_fd)

        session = PtySession(
            session_id=session_id,
            command=command,
            master_fd=master_fd,
            process=process,
        )
        _sessions[session_id] = session

        # One long-running reader per session
        async def _pty_reader() -> None:
            loop = asyncio.get_event_loop()
            while True:
                try:
                    data = await loop.run_in_executor(
                        None, os.read, session.master_fd, 4096
                    )
                    if not data:
                        break
                    ws = session.ws_holder[0]
                    if ws is not None:
                        try:
                            await ws.send_text(data.decode("utf-8", errors="replace"))
                        except Exception:
                            session.ws_holder[0] = None  # WS gone, discard data
                except OSError:
                    break

            # Process exited — notify attached WS (if any), clean up
            _sessions.pop(session_id, None)
            ws = session.ws_holder[0]
            if ws is not None:
                try:
                    code = session.process.returncode
                    await ws.send_json({"type": "cli_exit", "code": code})
                except Exception:
                    pass
            logger.info("[%s] Session %s process exited", command, session_id)

        session.read_task = asyncio.create_task(_pty_reader())
        logger.info("[%s] New session %s", command, session_id)

    # ── Attach this WebSocket ─────────────────────────────────────────────────
    session.ws_holder[0] = websocket

    try:
        await websocket.send_json({
            "type": "cli_ready",
            "command": command,
            "session_id": session_id,
            "resumed": resumed,
        })
    except Exception:
        session.ws_holder[0] = None
        return

    # ── Relay input from client → PTY ─────────────────────────────────────────
    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
                if msg.get("type") == "resize":
                    _set_pty_size(session.master_fd, msg["rows"], msg["cols"])
                    continue
            except (json.JSONDecodeError, KeyError):
                pass
            try:
                os.write(session.master_fd, text.encode("utf-8"))
            except OSError:
                break
    except WebSocketDisconnect:
        logger.info("[%s] Session %s WS disconnected", command, session_id)

    # ── Detach WS from session ────────────────────────────────────────────────
    if session.ws_holder[0] is websocket:
        session.ws_holder[0] = None

    if session.process.returncode is not None:
        return  # reader task already cleaned up the session

    # Keep the process alive; clean up after timeout
    async def _deferred_cleanup() -> None:
        try:
            await asyncio.sleep(SESSION_TIMEOUT)
            logger.info("[%s] Session %s timed out — terminating", command, session_id)
            _sessions.pop(session_id, None)
            await session.terminate()
        except asyncio.CancelledError:
            logger.debug("[%s] Session %s cleanup cancelled (reconnected)", command, session_id)

    session.cleanup_task = asyncio.create_task(_deferred_cleanup())
    logger.info(
        "[%s] Session %s kept alive for %ds", command, session_id, SESSION_TIMEOUT
    )
