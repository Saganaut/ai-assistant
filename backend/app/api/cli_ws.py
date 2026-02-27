import asyncio
import fcntl
import json
import logging
import os
import pty
import struct
import termios

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


def set_pty_size(fd: int, rows: int, cols: int) -> None:
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


async def run_cli_over_ws(websocket: WebSocket, command: str, args: list[str] | None = None):
    """Spawn a CLI command in a PTY and bridge it to a WebSocket."""
    await websocket.accept()

    master_fd, slave_fd = pty.openpty()
    process = None
    cmd = [command] + (args or [])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)
        slave_fd = -1

        await websocket.send_json({"type": "cli_ready", "command": command})

        loop = asyncio.get_event_loop()

        async def read_pty():
            while True:
                try:
                    data = await loop.run_in_executor(
                        None, os.read, master_fd, 4096
                    )
                    if not data:
                        break
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
                except OSError:
                    break

        read_task = asyncio.create_task(read_pty())

        try:
            while True:
                text = await websocket.receive_text()
                try:
                    msg = json.loads(text)
                    if msg.get("type") == "resize":
                        set_pty_size(master_fd, msg["rows"], msg["cols"])
                        continue
                except (json.JSONDecodeError, KeyError):
                    pass
                try:
                    os.write(master_fd, text.encode("utf-8"))
                except OSError:
                    break
        except WebSocketDisconnect:
            logger.info("%s CLI WebSocket disconnected", command)

        read_task.cancel()
        try:
            await read_task
        except asyncio.CancelledError:
            pass

    finally:
        if slave_fd != -1:
            os.close(slave_fd)
        try:
            os.close(master_fd)
        except OSError:
            pass
        if process and process.returncode is None:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except (ProcessLookupError, asyncio.TimeoutError):
                process.kill()

        try:
            code = process.returncode if process else -1
            await websocket.send_json({"type": "cli_exit", "code": code})
        except Exception:
            pass
