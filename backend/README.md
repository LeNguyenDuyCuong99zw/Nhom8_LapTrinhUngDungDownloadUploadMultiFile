# Backend — WebSocket server (Python)

Server WebSocket này hỗ trợ upload file theo các thao tác: `start`, `chunk`, `pause`, `resume`, `stop`, `complete` và resume theo offset.

## Mục lục

- [Cài đặt](#cài-đặt)
- [Chạy server](#chạy-server)
- [Client (async)](#client-async)
- [Giao thức WebSocket (JSON)](#giao-thức-websocket-json)
- [Thư mục lưu file](#thư-mục-lưu-file)
- [Lưu ý / Tips](#lưu-ý--tips)

## Cài đặt

Mở PowerShell và chạy:

```powershell
cd backend
python -m venv .venv
# PowerShell (dot-source the activation script). Nếu gặp lỗi policy, chạy PowerShell as Administrator hoặc dùng CMD
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Trên CMD (nếu cần):

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy server

```powershell
python server.py
```

Mặc định server lắng nghe tại `ws://localhost:8765`.

Thiết lập qua biến môi trường (tuỳ ý):

- `WS_HOST` — mặc định: `localhost`
- `WS_PORT` — mặc định: `8765`

## Client (async)

`client.py` là client bất đồng bộ (asyncio) dùng để upload/pause/resume/stop qua WebSocket.

### Chạy client

```powershell
# Upload file với cấu hình mặc định
python client.py "D:/path/to/file.zip"

# Tùy chỉnh WebSocket URL và chunk size
python client.py "D:/path/to/file.zip" --ws ws://localhost:8765/ws --chunk 131072

# Truyền sẵn file id (để resume giữa các lần chạy)
python client.py "D:/path/to/file.zip" --id my-file-id-123
```

### Phím tắt (interactive client)

- `p` : pause
- `r` : resume
- `s` : stop (xóa file `.part` trên server nếu `delete=True`)
- `q` : quit (gửi stop `delete=False` rồi thoát)

## Giao thức WebSocket (JSON)

Client và server giao tiếp bằng JSON. Các event chính:

1. Start

Client -> Server

```json
{
  "action": "start",
  "fileId": "unique-id",
  "fileName": "example.zip",
  "fileSize": 12345678
}
```

Server -> Client

```json
{
  "event": "start-ack",
  "fileId": "unique-id",
  "offset": 0,
  "status": "active"
}
```

2. Chunk

Client -> Server

```json
{
  "action": "chunk",
  "fileId": "unique-id",
  "offset": 0,
  "data": "<base64>"
}
```

Server -> Client (ví dụ tiến trình)

```json
{
  "event": "progress",
  "fileId": "unique-id",
  "offset": 65536,
  "receivedBytes": 65536,
  "percent": 12.34
}
```

Nếu offset không khớp, server trả về:

```json
{
  "event": "offset-mismatch",
  "fileId": "unique-id",
  "expected": 65536,
  "received": 0
}
```

3. Pause

Client -> Server

```json
{ "action": "pause", "fileId": "unique-id" }
```

Server -> Client

```json
{ "event": "pause-ack", "fileId": "unique-id", "offset": 65536 }
```

4. Resume

Client -> Server

```json
{ "action": "resume", "fileId": "unique-id" }
```

Server -> Client

```json
{ "event": "resume-ack", "fileId": "unique-id", "offset": 65536 }
```

5. Stop

Client -> Server

```json
{ "action": "stop", "fileId": "unique-id", "delete": true }
```

Server -> Client

```json
{ "event": "stop-ack", "fileId": "unique-id" }
```

6. Complete

Client -> Server

```json
{ "action": "complete", "fileId": "unique-id" }
```

Server -> Client

```json
{
  "event": "complete-ack",
  "fileId": "unique-id",
  "filePath": "D:/path/to/uploads/example.zip"
}
```

7. Error

Server -> Client (mẫu)

```json
{ "event": "error", "fileId": "unique-id", "error": "Reason" }
```

## Thư mục lưu file

Mặc định lưu ở `backend/uploads`. File đang upload có hậu tố `.part`; khi hoàn tất server sẽ đổi tên thành file cuối.

## Lưu ý / Tips

- `client.py` dùng `asyncio` và có luồng nhận message song song để phản hồi tiến trình nhanh.
- Điều chỉnh `--chunk` để thay đổi kích thước chunk (mặc định trong project là ~64KB).
- `stop(delete=True)` sẽ xóa file `.part` trên server.

Để chạy giao diện tĩnh (frontend) đơn giản cho thử nghiệm:

```powershell
cd frontend
python -m http.server 8000

# Sau đó mở trình duyệt: http://localhost:8000
```
