import asyncio
import base64
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterable

import websockets
from logger import setup_logger

# Thiết lập logger cho client
logger = setup_logger("client")

DEFAULT_WS_URL = os.environ.get("WS_URL", "ws://localhost:8765/ws")
CHUNK_SIZE = 64 * 1024  # 64KB


@dataclass
class UploadState:
    file_id: str
    file_path: Path
    file_size: int
    offset: int = 0
    is_paused: bool = False
    is_stopped: bool = False


class AsyncUploader:
    def __init__(self, ws_url: str = DEFAULT_WS_URL, chunk_size: int = CHUNK_SIZE) -> None:
        self.ws_url = ws_url
        self.chunk_size = chunk_size
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.state: Optional[UploadState] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # start in running state
        logger.debug("AsyncUploader initialized with ws_url=%s, chunk_size=%d", ws_url, chunk_size)

    async def __aenter__(self):
        logger.debug("Connecting to WebSocket: %s", self.ws_url)
        self.websocket = await websockets.connect(self.ws_url, max_size=8 * 1024 * 1024)
        self._recv_task = asyncio.create_task(self._receiver())
        logger.info("Connected to WebSocket server")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        import contextlib
        if self._recv_task:
            self._recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recv_task
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        logger.debug("WebSocket connection closed")

    async def _receiver(self):
        try:
            assert self.websocket is not None
            async for message in self.websocket:
                await self._handle_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Receiver error: %s", exc, exc_info=True)

    async def _handle_message(self, message: str):
        import json
        try:
            data = json.loads(message)
        except Exception:
            logger.warning("Received non-JSON message: %s", message)
            return

        event = data.get("event")
        if not self.state:
            logger.debug("Received message without state: %s", data)
            return

        if event == "start-ack":
            self.state.offset = int(data.get("offset", 0))
            logger.info("Start acknowledged: resume at offset=%d for %s", 
                       self.state.offset, self.state.file_path.name)
        elif event == "progress":
            off = int(data.get("offset", 0))
            self.state.offset = off
            percent = data.get("percent")
            logger.debug("Progress: offset=%d (%s%%) for %s", 
                        off, percent, self.state.file_path.name)
        elif event == "pause-ack":
            logger.info("Pause acknowledged: offset=%s for %s", 
                       data.get('offset'), self.state.file_path.name)
        elif event == "resume-ack":
            off = int(data.get("offset", 0))
            self.state.offset = off
            logger.info("Resume acknowledged: offset=%d for %s", 
                       off, self.state.file_path.name)
        elif event == "stop-ack":
            logger.info("Stop acknowledged for %s", self.state.file_path.name)
        elif event == "complete-ack":
            logger.info("Upload completed: path=%s for %s", 
                       data.get('filePath'), self.state.file_path.name)
        elif event == "offset-mismatch":
            expected = int(data.get("expected", 0))
            logger.warning("Offset mismatch, expected=%d for %s", 
                          expected, self.state.file_path.name)
            self.state.offset = expected
        elif event == "error":
            logger.error("Server error: %s for %s", 
                        data.get('error'), self.state.file_path.name)
        else:
            logger.debug("Unknown event: %s", data)

    async def start(self, file_path: str, file_id: Optional[str] = None):
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        if file_id is None:
            file_id = uuid.uuid4().hex
            logger.debug("Generated file_id: %s", file_id)

        self.state = UploadState(
            file_id=file_id,
            file_path=path,
            file_size=path.stat().st_size,
        )

        logger.info("Starting upload: file=%s, size=%d bytes, id=%s", 
                   path.name, self.state.file_size, file_id)

        await self._send_json({
            "action": "start",
            "fileId": self.state.file_id,
            "fileName": path.name,
            "fileSize": self.state.file_size,
        })

    

