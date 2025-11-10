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


class DownloadManager:
    def __init__(self):
        self.downloads: Dict[str, DownloadSession] = {}
        self.active_downloads: Dict[str, dict] = {}
        logger.info("DownloadManager initialized")
        
    def generate_session_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:12]
        
    def create_session(self, url: str, filename: Optional[str] = None) -> DownloadSession:
        session_id = self.generate_session_id()
        if not filename:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or "download"
        
        session = DownloadSession(session_id, url, filename)
        self.downloads[session_id] = session
        logger.info(f"Created download session: {session_id} for {url}")
        return session
    
    def get_session(self, session_id: str) -> Optional[DownloadSession]:
        return self.downloads.get(session_id)
    
    async def start_download(self, session_id: str, websocket: WebSocketServerProtocol) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
            
        if session_id in self.active_downloads:
            return False
            
        self.active_downloads[session_id] = {
            'session': session,
            'websocket': websocket,
            'task': None
        }
        
        # Start download task
        task = asyncio.create_task(self._download_file(session, websocket))
        self.active_downloads[session_id]['task'] = task
        
        return True
    
    async def pause_download(self, session_id: str):
        if session_id in self.active_downloads:
            download_info = self.active_downloads[session_id]
            if download_info['task']:
                download_info['task'].cancel()
            download_info['session'].status = "paused"
    
    async def resume_download(self, session_id: str, websocket: WebSocketServerProtocol) -> bool:
        session = self.get_session(session_id)
        if session and session.status == "paused":
            return await self.start_download(session_id, websocket)
        return False
    
    async def stop_download(self, session_id: str):
        if session_id in self.active_downloads:
            download_info = self.active_downloads[session_id]
            if download_info['task']:
                download_info['task'].cancel()
            
            # Clean up temp file
            session = download_info['session']
            if session.temp_file_path and os.path.exists(session.temp_file_path):
                try:
                    os.remove(session.temp_file_path)
                except:
                    pass
            
            del self.active_downloads[session_id]
            if session_id in self.downloads:
                del self.downloads[session_id]
    
    async def _download_file(self, session: DownloadSession, websocket: WebSocketServerProtocol):
        try:
            session.status = "active"
            logger.info(f"Starting download: {session.session_id}")
            
            # Send start acknowledgment
            await self.send(websocket, {
                'event': 'download-start-ack',
                'fileId': session.session_id,
                'filename': session.filename,
                'offset': session.downloaded_bytes
            })
            
            timeout = aiohttp.ClientTimeout(total=300, connect=30)
            headers = {}
            
            # Resume support
            if session.downloaded_bytes > 0:
                headers['Range'] = f'bytes={session.downloaded_bytes}-'
            
            async with aiohttp.ClientSession(timeout=timeout) as client_session:
                async with client_session.get(session.url, headers=headers) as response:
                    
                    # Get total size
                    if session.total_size == 0:
                        content_length = response.headers.get('Content-Length')
                        if content_length:
                            if 'Range' in headers:
                                session.total_size = session.downloaded_bytes + int(content_length)
                            else:
                                session.total_size = int(content_length)
                    
                    # Send size info
                    await self.send(websocket, {
                        'event': 'download-info',
                        'fileId': session.session_id,
                        'totalSize': session.total_size,
                        'supportsResume': response.status == 206
                    })
                    
                    # Open file for writing
                    mode = 'ab' if session.downloaded_bytes > 0 else 'wb'
                    async with aiofiles.open(session.temp_path(), mode) as f:
                        
                        chunk_size = 64 * 1024  # 64KB chunks
                        last_progress_time = time.time()
                        
                        async for chunk in response.content.iter_chunked(chunk_size):
                            if session.status != "active":
                                break
                                
                            await f.write(chunk)
                            session.downloaded_bytes += len(chunk)
                            
                            # Send progress every 250ms
                            now = time.time()
                            if now - last_progress_time > 0.25:
                                progress = 0
                                if session.total_size > 0:
                                    progress = (session.downloaded_bytes / session.total_size) * 100
                                
                                await self.send(websocket, {
                                    'event': 'download-progress',
                                    'fileId': session.session_id,
                                    'downloadedBytes': session.downloaded_bytes,
                                    'totalSize': session.total_size,
                                    'progress': progress
                                })
                                
                                last_progress_time = now
                    
                    # Download completed
                    if session.downloaded_bytes >= session.total_size or session.total_size == 0:
                        session.status = "completed"
                        
                        # Move to final location (uploads directory)
                        final_path = DOWNLOADS_DIR / session.filename
                        counter = 1
                        base_name = final_path.stem
                        ext = final_path.suffix
                        
                        while final_path.exists():
                            final_path = DOWNLOADS_DIR / f"{base_name}_{counter}{ext}"
                            counter += 1
                        
                        os.rename(session.temp_path(), str(final_path))
                        
                        await self.send(websocket, {
                            'event': 'download-complete',
                            'fileId': session.session_id,
                            'filename': final_path.name,
                            'filePath': str(final_path),
                            'totalSize': session.downloaded_bytes
                        })
                        
        except asyncio.CancelledError:
            session.status = "paused"
            logger.info(f"Download paused: {session.session_id}")
            
        except Exception as e:
            session.status = "error"
            logger.error(f"Download error for {session.session_id}: {e}")
            
            await self.send(websocket, {
                'event': 'download-error',
                'fileId': session.session_id,
                'error': str(e)
            })
        
        finally:
            # Clean up
            if session.session_id in self.active_downloads:
                del self.active_downloads[session.session_id]
    
    async def send(self, websocket: WebSocketServerProtocol, message: dict):
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")


class UploadManager:
    def __init__(self) -> None:
        self.file_id_to_session: Dict[str, UploadSession] = {}
        self.connection_to_sessions: Dict[WebSocketServerProtocol, Dict[str, UploadSession]] = {}
        self.connection_auth: Dict[WebSocketServerProtocol, dict] = {}  # Store auth info per connection
        logger.info("UploadManager initialized with remote upload capability")

    def register_connection(self, ws: WebSocketServerProtocol) -> None:
        if ws not in self.connection_to_sessions:
            self.connection_to_sessions[ws] = {}
        if ws not in self.connection_auth:
            self.connection_auth[ws] = {'authenticated': False, 'user': None, 'token': None}
        logger.debug("Connection registered: %s", ws.remote_address)

    def authenticate_connection(self, ws: WebSocketServerProtocol, token: str, user: dict) -> bool:
        """Authenticate a WebSocket connection"""
        if not auth_db or not token:
            return False
            
        # Verify token với auth database
        verified_user = auth_db.get_user_by_token(token)
        if verified_user:
            self.connection_auth[ws] = {
                'authenticated': True,
                'user': verified_user,
                'token': token
            }
            # logger.debug(f"Connection authenticated: {ws.remote_address} as {verified_user['username']}")
            return True
        
        return False

    def get_connection_auth(self, ws: WebSocketServerProtocol) -> dict:
        """Lấy thông tin authentication của connection"""
        return self.connection_auth.get(ws, {'authenticated': False, 'user': None, 'token': None})

    def unregister_connection(self, ws: WebSocketServerProtocol) -> None:
        sessions = self.connection_to_sessions.pop(ws, {})
        self.connection_auth.pop(ws, None)  # Clean up auth info
        for session in sessions.values():
            if session.status == "active":
                session.status = "paused"
                logger.info("Session paused due to disconnect: %s (%s)", 
                           session.file_id, session.file_name)
        logger.debug("Connection unregistered: %s", ws.remote_address)

    def get_or_create_session(self, ws: WebSocketServerProtocol, file_id: str, file_name: str, file_size: int) -> UploadSession:
        safe_name = os.path.basename(file_name)
        temp_path = TEMP_DIR / f"{file_id}_{safe_name}"

        # Get auth info
        auth_info = self.get_connection_auth(ws)
        
        # FIX: Require authentication for new uploads
        if not auth_info['authenticated']:
            logger.warning("Attempted upload without authentication: %s", ws.remote_address)
            raise ValueError("Authentication required for file upload")

        existing = self.file_id_to_session.get(file_id)
        if existing:
            existing.file_name = safe_name
            existing.file_size = file_size
            # Update auth info if not set
            if not existing.user_id and auth_info['authenticated']:
                existing.user_id = auth_info['user']['id']
                existing.user_token = auth_info['token']
            existing.temp_file_path = temp_path
            if existing.temp_path().exists():
                existing.bytes_received = existing.temp_path().stat().st_size
                logger.debug("Resuming existing session: %s, offset=%d", file_id, existing.bytes_received)
            return existing

        session = UploadSession(
            file_id=file_id,
            file_name=safe_name,
            file_size=file_size,
            status="active",
            bytes_received=0,
            temp_file_path=temp_path,
            user_id=auth_info['user']['id'],  # FIX: Always require authenticated user
            user_token=auth_info['token']
        )
        
        if session.temp_path().exists():
            session.bytes_received = session.temp_path().stat().st_size
            logger.info("Found existing partial file: %s, size=%d bytes", 
                       session.temp_path(), session.bytes_received)
        
        # Thêm file vào database với status "uploading"
        try:
            temp_filename = f"{file_id}_{safe_name}"
            session.db_id = db.add_file(
                filename=safe_name,
                original_filename=file_name,
                size=file_size,
                uploader="WebSocket Client",
                temp_path=temp_filename
            )
            logger.info(f"File added to database: {file_name} (DB ID: {session.db_id})")
        except Exception as e:
            logger.error(f"Failed to add file to database: {e}")
            session.db_id = None
        
        self.file_id_to_session[file_id] = session
        logger.info("Created new upload session: %s (%s), size=%d bytes", 
                   file_id, safe_name, file_size)
        return session

    def remove_session(self, file_id: str) -> None:
        if file_id in self.file_id_to_session:
            session = self.file_id_to_session[file_id]
            logger.debug("Removing session: %s (%s)", file_id, session.file_name)
            del self.file_id_to_session[file_id]

    async def broadcast_to_session(self, session: UploadSession, message: dict) -> None:
        """Gửi message đến tất cả client đang kết nối với session này"""
        for ws, sessions in self.connection_to_sessions.items():
            if session.file_id in sessions:
                try:
                    await self.send(ws, message)
                except Exception as e:
                    logger.warning("Failed to send message to client: %s", e)

 