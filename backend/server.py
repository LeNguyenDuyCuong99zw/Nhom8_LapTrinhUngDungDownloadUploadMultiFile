import asyncio
import base64
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs
import aiohttp
import aiofiles

import websockets
from websockets.server import WebSocketServerProtocol
from logger import setup_logger
from database import db

# Import auth database để verify tokens
try:
    from auth_database import AuthDatabase
    auth_db = AuthDatabase()
except ImportError:
    auth_db = None
    print("Warning: AuthDatabase not available")

# Thiết lập logger cho server
logger = setup_logger("server")

# Cấu hình remote server
REMOTE_UPLOAD_URL = os.environ.get("REMOTE_UPLOAD_URL", "http://localhost:5000/api/upload")
REMOTE_SERVER_TOKEN = os.environ.get("REMOTE_SERVER_TOKEN", "your-secret-token")

# Thư mục tạm để lưu file trước khi gửi đi
TEMP_DIR = Path(__file__).parent / "temp_uploads"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Thư mục lưu files đã download
DOWNLOADS_DIR = Path(__file__).parent / "remote_uploads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class UploadSession:
    file_id: str
    file_name: str
    file_size: int
    status: str = "active"  # active | paused | completed | stopped | error | uploading
    bytes_received: int = 0
    temp_file_path: Path = field(default_factory=Path)
    remote_file_id: Optional[str] = None
    file_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    db_id: Optional[int] = None  # ID từ SQLite database
    user_id: Optional[int] = None  # ID của user upload
    user_token: Optional[str] = None  # Auth token của user

    def temp_path(self) -> Path:
    # session.temp_file_path: .../temp_uploads/<file-id>_<name>
        return self.temp_file_path.with_name(self.temp_file_path.name + ".part")

@dataclass
class DownloadSession:
    session_id: str
    url: str
    filename: str
    total_size: int = 0
    downloaded_bytes: int = 0
    status: str = "pending"  # pending | active | paused | completed | error | stopped
    temp_file_path: Optional[str] = None
    last_update: float = field(default_factory=time.time)
    
    def temp_path(self) -> str:
        if not self.temp_file_path:
            safe_filename = "".join(c for c in self.filename if c.isalnum() or c in "._- ")
            self.temp_file_path = str(TEMP_DIR / f"{self.session_id}_{safe_filename}.download")
        return self.temp_file_path


