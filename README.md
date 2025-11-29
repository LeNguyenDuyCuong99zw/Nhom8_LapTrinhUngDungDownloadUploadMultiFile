<div align="center">

# TransferFlow Hub

## Hệ thống Upload và Quản lý Files với Phân Quyền

[![Python](https://img.shields.io/badge/Python-3.8+-3670A0?style=for-the-badge&logo=python)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite)](https://www.sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

Ứng dụng quản lý chuyển file chuyên nghiệp với khả năng upload files lên remote server, quản lý files thông qua giao diện web riêng biệt và hệ thống phân quyền người dùng đầy đủ.

</div>

---

## 📋 Thông tin Dự án

| Thông tin      | Chi tiết                                  |
| -------------- | ----------------------------------------- |
| **Trường**     | Đại học Giao thông Vận tải TP Hồ Chí Minh |
| **Môn học**    | Lập trình mạng                            |
| **Giảng viên** | Mai Ngọc Châu                             |
| **Tên dự án**  | TransferFlow Hub                          |

### 👥 Thành viên nhóm

| STT | Họ và tên           |
| --- | ------------------- |
| 1   | Lê Nguyễn Duy Cường |
| 2   | Lê Minh Hữu Luân    |
| 3   | Nguyễn Gia Quy      |
| 4   | Nguyễn Thị Thùy Vân |
| 5   | Võ Đặng Vũ Phong    |
| 6   | Mã Nhật Thanh       |

---

## ✨ Tính năng chính

| Tính năng                  | Mô tả                                                  |
| -------------------------- | ------------------------------------------------------ |
| 🔐 **Hệ thống phân quyền** | Đăng nhập/đăng ký với quản lý quyền hạn (Admin/User)   |
| 👤 **User Isolation**      | Mỗi user chỉ thấy và truy cập files của chính mình     |
| 🗑️ **Thùng rác**           | Khôi phục files trong 7-30 ngày (tùy thuộc role)       |
| 👁️ **File Preview**        | Xem trước ảnh, PDF, video, audio và text files         |
| ☁️ **Remote Upload**       | Upload files lên remote server thay vì lưu local       |
| 📁 **Quản lý Folders**     | Tạo, xóa, tổ chức folders với nested support           |
| 📊 **Thống kê Real-time**  | Dashboard hiển thị files, folders, dung lượng của user |
| 🔍 **Tìm kiếm & Lọc**      | Tìm files theo tên, lọc theo loại file                 |
| ⬇️ **Download Files**      | Tải files từ remote server                             |
| 🔒 **Session Management**  | Xác thực an toàn với token expiration                  |

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────┐    WebSocket    ┌─────────────────┐    HTTP POST    ┌──────────────────┐
│   Frontend      │ ──────────────► │  WebSocket      │ ──────────────► │  File Manager    │
│   (Upload UI)   │                 │  Server         │                 │  Server (Flask)  │
│  http:8000      │                 │  ws://8765      │                 │  http://5000     │
└─────────────────┘                 └─────────────────┘                 └──────────────────┘
                                              │                              │
                                              │                 ┌────────────┴────────────┐
                                              ▼                 │                         │
                                    ┌─────────────────┐         ▼                         ▼
                                    │  Temp Storage   │   ┌──────────────┐          ┌──────────────┐
                                    │  (Local Cache)  │   │    Auth DB   │          │   Files DB   │
                                    │  temp_uploads/  │   │   (SQLite)   │          │  (SQLite)    │
                                    └─────────────────┘   │ auth.db      │          │  files.db    │
                                                          └──────────────┘          └──────────────┘
                                                                │
                                                                ▼
                                                    ┌──────────────────────┐
                                                    │  Remote Storage      │
                                                    │  remote_uploads/     │
                                                    │  └── {username}/     │
                                                    └──────────────────────┘
```

### 📡 Luồng xử lý

1. **Frontend** → Upload files qua kéo thả
2. **WebSocket** → Gửi files đến server
3. **Temp Storage** → Lưu tạm thời
4. **Remote Upload** → Chuyển đến File Manager
5. **Storage** → Lưu vào thư mục user
6. **Database** → Ghi metadata
7. **Management** → User quản lý qua web UI

---

## 🔐 Cơ sở dữ liệu

### 📊 Lược đồ Database

#### Bảng `users` - Quản lý người dùng

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'user',  -- 'admin' hoặc 'user'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login TIMESTAMP
);
```

#### Bảng `files` - Lưu trữ metadata file

```sql
CREATE TABLE files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  size INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  folder_id TEXT,
  file_path TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Bảng `folders` - Quản lý thư mục

```sql
CREATE TABLE folders (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  parent_id TEXT,
  user_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Bảng `recycle_bin` - Thùng rác

```sql
CREATE TABLE recycle_bin (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_file_id INTEGER,
  filename TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  size INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  file_path TEXT NOT NULL,
  deleted_by INTEGER,
  deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  restore_deadline TIMESTAMP,
  status TEXT DEFAULT 'deleted',
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (deleted_by) REFERENCES users(id)
);
```

#### Bảng `sessions` - Quản lý phiên đăng nhập

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 📁 Cấu trúc Dự án

```
Nhom8_LapTrinhUngDungDownloadUploadMultiFile/
│
├── backend/                           # Backend services
│   ├── server.py                      # WebSocket server (port 8765)
│   ├── file_manager.py                # Flask web server (port 5000)
│   ├── auth_database.py               # Authentication helper
│   ├── database.py                    # File database helper
│   ├── migrate_database.py            # Database migration script
│   ├── create_admin.py                # Tạo admin account
│   ├── client.py                      # Test client
│   ├── logger.py                      # Logging utility
│   │
│   ├── templates/                     # HTML templates
│   │   ├── index.html                 # File manager UI
│   │   ├── login.html                 # Login page
│   │   ├── register.html              # Register page
│   │   └── admin.html                 # Admin panel
│   │
│   ├── temp_uploads/                  # Temporary file storage
│   ├── remote_uploads/                # Final storage
│   │   ├── admin/
│   │   ├── duy11ff/
│   │   ├── duycuong12/
│   │   └── luan11/
│   │
│   ├── auth.db                        # Authentication database (SQLite)
│   ├── files.db                       # File metadata database (SQLite)
│   ├── requirements.txt               # Python dependencies
│   ├── README.md                      # Backend documentation
│   └── logging.md                     # Logging configuration
│
├── frontend/                          # Frontend application
│   ├── index.html                     # Upload UI
│   ├── script.js                      # Upload logic
│   └── style.css                      # Styles
│
├── README.md                          # This file
├── start_all.bat                      # Batch script to start all servers
├── check_ports.bat                    # Check port availability
└── .env                               # Environment variables (optional)
```

---

## 🚀 Cài đặt và Chạy

### ⚙️ Yêu cầu hệ thống

- **Python**: 3.8 hoặc cao hơn
- **pip**: Package manager cho Python
- **Trình duyệt web**: Chrome, Firefox, Edge, Safari

### 📦 Bước 1: Cài đặt Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Các package sẽ được cài đặt:

- Flask (web framework)
- websockets (WebSocket support)
- sqlite3 (database)
- Werkzeug (utilities)

### 🗄️ Bước 2: Khởi tạo Database

```bash
cd backend
python auth_database.py
python migrate_database.py
```

**Default Accounts được tạo:**

| Username | Password | Role  | Mô tả                                    |
| -------- | -------- | ----- | ---------------------------------------- |
| admin    | admin123 | admin | Quản trị viên - 30 ngày lưu thùng rác    |
| testuser | test123  | user  | Người dùng thường - 7 ngày lưu thùng rác |

### ⚡ Bước 3: Chạy File Manager Server

```bash
cd backend
python file_manager.py
```

✅ Server chạy trên: **http://localhost:5000**

### 🔌 Bước 4: Chạy WebSocket Server

Mở terminal mới và chạy:

```bash
cd backend
python server.py
```

✅ Server chạy trên: **ws://localhost:8765**

### 🌐 Bước 5: Chạy Frontend (Upload UI)

Mở terminal khác và chạy:

```bash
cd frontend
python -m http.server 8000
```

✅ Frontend chạy trên: **http://localhost:8000**

### 💡 Quick Start - Chạy tất cả cùng lúc

**Windows:**

```bash
start_all.bat
```

**Linux/Mac:**

```bash
./start_all.sh
```

### 🆕 Lưu ý khi khởi động dự án mới

Nếu bạn vừa copy code mới và **chưa có file `auth.db`**:

```bash
cd backend
python create_admin.py
```

Sau đó đăng nhập bằng:

- **Username**: admin
- **Password**: admin123

---

## ⚙️ Cấu hình

### 🔑 Environment Variables

Tạo file `.env` trong thư mục `backend` (tùy chọn):

```env
# Server Configuration
REMOTE_UPLOAD_URL=http://localhost:5000/api/upload
REMOTE_SERVER_TOKEN=your-secret-token

# WebSocket Configuration
WS_HOST=localhost
WS_PORT=8765

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# File Upload
MAX_CONTENT_LENGTH=536870912  # 512MB
UPLOAD_FOLDER=remote_uploads
```

### 📝 Tham số Cấu hình

| Tham số               | Mô tả                            | Mặc định                         |
| --------------------- | -------------------------------- | -------------------------------- |
| `REMOTE_UPLOAD_URL`   | URL server quản lý files         | http://localhost:5000/api/upload |
| `REMOTE_SERVER_TOKEN` | Token xác thực (local có thể bỏ) | -                                |
| `WS_HOST`             | Host của WebSocket server        | localhost                        |
| `WS_PORT`             | Port của WebSocket server        | 8765                             |
| `MAX_CONTENT_LENGTH`  | Kích thước file tối đa (bytes)   | 512MB                            |
| `UPLOAD_FOLDER`       | Thư mục lưu files                | remote_uploads                   |

---

## 📖 Hướng dẫn Sử dụng

### 1️⃣ Đăng nhập / Đăng ký

1. Mở trình duyệt và truy cập: **http://localhost:5000**
2. Chọn:
   - **Đăng nhập**: Sử dụng tài khoản mặc định hoặc tài khoản của bạn
   - **Đăng ký**: Tạo tài khoản mới

**Tài khoản mặc định:**

```
Admin:     admin / admin123
TestUser:  testuser / test123
```

### 2️⃣ Upload Files

1. Đăng nhập thành công → Giao diện File Manager
2. Click nút **"📤 Upload Files"** → Chuyển đến http://localhost:8000
3. **Cách upload**:
   - ✅ **Kéo thả files** vào vùng upload
   - ✅ **Click nút "Browse Files"** để chọn từ máy tính
4. Chờ upload hoàn tất (các files được lưu vào thư mục của user)
5. **Trở về File Manager** để xem files vừa upload

### 3️⃣ Quản lý Files

| Thao tác          | Mô tả                                      |
| ----------------- | ------------------------------------------ |
| 📂 **Tạo Folder** | Click "Tạo folder mới" → Nhập tên → OK     |
| 🔍 **Tìm kiếm**   | Nhập tên file → Tìm kiếm tức thời          |
| 🔀 **Move File**  | Chọn file → Kéo vào folder hoặc menu move  |
| ⬇️ **Download**   | Click "⬇️ Download" bên cạnh file          |
| 👁️ **Preview**    | Click "👁️ Preview" để xem trước file       |
| 🗑️ **Xóa**        | Click "🗑️ Xóa" → File chuyển vào thùng rác |

### 4️⃣ Xem thống kê

Dashboard hiển thị thông tin của **user hiện tại**:

- 📊 **Tổng files**: Số lượng files
- 📁 **Tổng folders**: Số lượng thư mục
- 💾 **Dung lượng sử dụng**: GB/MB
- 🏷️ **Loại files**: Số lượng kiểu file khác nhau

### 5️⃣ Thùng Rác (Recycle Bin)

```
📌 Tính năng:
├── 🗑️ Xem tất cả files đã xóa
├── ♻️ Khôi phục files về bình thường
├── 💀 Xóa vĩnh viễn (không thể khôi phục)
└── ⏰ Thời hạn khôi phục
    ├── User: 7 ngày
    └── Admin: 30 ngày
```

**Sử dụng:**

1. Click nút "🗑️ Thùng rác" ở menu
2. Xem danh sách files đã xóa
3. Chọn tác vụ:
   - **♻️ Khôi phục**: Đưa file về thư mục gốc
   - **💀 Xóa vĩnh viễn**: Xóa hoàn toàn khỏi hệ thống

### 6️⃣ File Preview

**Hỗ trợ các loại file:**

| Loại         | Format                        |
| ------------ | ----------------------------- |
| 🖼️ **Ảnh**   | JPG, PNG, GIF, WebP, BMP      |
| 📄 **PDF**   | PDF (xem qua viewer)          |
| 🎬 **Video** | MP4, WebM, OGG                |
| 🔊 **Audio** | MP3, WAV, OGG                 |
| 📝 **Text**  | TXT, JSON, XML, HTML, CSS, JS |

**Cách sử dụng:**

1. Click "👁️ Preview" bên cạnh file
2. File sẽ hiển thị trong modal popup
3. Có thể zoom, phát, hoặc download

### 7️⃣ Đăng xuất

1. Click **"👤 Đăng xuất"** ở góc trên phải
2. Session được xóa → Chuyển về trang login
3. Toàn bộ files vẫn được bảo lưu

---

## 🔒 Bảo mật

### Các biện pháp bảo mật được áp dụng:

| Biện pháp                     | Mô tả                               | Lợi ích                               |
| ----------------------------- | ----------------------------------- | ------------------------------------- |
| 🔐 **Session Authentication** | Sử dụng secure token với expiration | Tránh unauthorized access             |
| 🔑 **Password Hashing**       | PBKDF2 + salt cho mỗi user          | Nếu db bị leak, passwords vẫn an toàn |
| 👤 **User Isolation**         | User chỉ thấy files của chính họ    | Dữ liệu hoàn toàn riêng tư            |
| 📁 **File Segregation**       | Files lưu riêng theo username       | Phân tách hoàn toàn giữa users        |
| ⏰ **Auto Logout**            | Token expire → tự động logout       | Tránh session hijacking               |
| ✅ **Authorization Check**    | Kiểm tra quyền trên mọi API         | Chặn unauthorized requests            |
| 🛡️ **Secure Filenames**       | Sử dụng `secure_filename`           | Tránh path traversal attacks          |
| 🔍 **Input Validation**       | Kiểm tra tên file, kích thước       | Xác thực dữ liệu input                |

### 🔄 Session & Token

```
Login → Tạo token → Lưu vào cookie → Gửi theo request
        ↓
      Kiểm tra token trong middleware
        ↓
      Token valid? → YES → Allow request
                   → NO  → Redirect to login
        ↓
Token expire → Auto logout
```

### 👮 Role-based Access Control (RBAC)

```
ADMIN Role:
├── Quản lý tất cả users
├── Xem admin panel
├── Thùng rác 30 ngày
└── Full access

USER Role:
├── Quản lý files của chính mình
├── Thùng rác 7 ngày
└── Limited access
```

---

## 🔧 Troubleshooting

### ❌ Lỗi thường gặp và cách khắc phục

#### 1. Lỗi: Không thể đăng nhập

```
Triệu chứng: "Invalid username/password" hoặc Access denied
```

**Giải pháp:**

```bash
# Kiểm tra database
cd backend
ls -la auth.db  # Hoặc dir auth.db trên Windows

# Tạo lại database
python auth_database.py
python create_admin.py
```

**Nguyên nhân phổ biến:**

- Database bị corrupted
- Admin user chưa được tạo
- Sai username/password

#### 2. Lỗi: "Connection refused" - Port đã sử dụng

```
Triệu chứng: Address already in use on port 5000/8765
```

**Giải pháp:**

```bash
# Kiểm tra ports
netstat -ano | findstr "5000\|8765"  # Windows
lsof -i :5000,8765                   # Linux/Mac

# Sử dụng port khác
# Chỉnh sửa file config hoặc environment
```

#### 3. Lỗi: Database Schema Error

```
Triệu chứng: Table not found, Column not found
```

**Giải pháp:**

```bash
cd backend

# Xóa database cũ
rm auth.db files.db  # Linux/Mac
del auth.db files.db # Windows

# Tạo lại
python auth_database.py
python migrate_database.py
```

#### 4. Lỗi: Files không hiển thị sau upload

```
Triệu chứng: Upload thành công nhưng file không có trong danh sách
```

**Kiểm tra danh sách:**

- ✅ Đã đăng nhập đúng user chưa?
- ✅ WebSocket server có chạy không?
- ✅ File Manager server có chạy không?
- ✅ Check thư mục `remote_uploads/{username}/`

#### 5. Lỗi: WebSocket Connection Failed

```
Triệu chứng: "Cannot connect to WebSocket server" hoặc upload failed
```

**Giải pháp:**

```bash
# Kiểm tra WebSocket server đang chạy
# Terminal 1: Chạy file manager
cd backend && python file_manager.py

# Terminal 2: Chạy WebSocket server
cd backend && python server.py

# Terminal 3: Chạy frontend
cd frontend && python -m http.server 8000
```

### 📋 Xem Logs

**WebSocket Server Logs:**

```
Terminal sẽ hiển thị tất cả upload events:
[2025-11-29 10:15:30] Client connected: ws://localhost:8765
[2025-11-29 10:15:35] File received: document.pdf (2.5MB)
```

**File Manager Server Logs:**

```
Terminal sẽ hiển thị tất cả API calls:
127.0.0.1 - - [29/Nov/2025 10:15:30] "POST /api/upload HTTP/1.1" 200
127.0.0.1 - - [29/Nov/2025 10:15:31] "GET /api/files HTTP/1.1" 200
```

**Frontend Console Logs:**

```
F12 → Console tab
[INFO] Upload started: 1 file(s)
[INFO] Connected to WebSocket
[SUCCESS] Upload completed!
```

### 🐛 Debug Mode

Để bật chi tiết logging:

```bash
# Thêm vào backend/server.py hoặc file_manager.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 📞 Khi cần support

Cung cấp thông tin sau:

1. **OS**: Windows / Linux / Mac
2. **Python version**: `python --version`
3. **Error message**: Copy error từ terminal
4. **Steps to reproduce**: Cách bạn tái tạo lỗi
5. **Screenshots**: Nếu cần

---

## 🔄 Workflow - Luồng xử lý Upload

```
┌─────────────────┐
│   User Login    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ File Manager UI │ (http://localhost:5000)
│  - View Files   │
│  - Create Dir   │
│  - Manage Files │
└────────┬────────┘
         │
         │ Click "Upload Files"
         ▼
┌──────────────────┐
│  Upload UI       │ (http://localhost:8000)
│  - Drag & Drop   │
│  - Browse Files  │
└────────┬─────────┘
         │
         │ Select files
         ▼
┌──────────────────┐
│ WebSocket Client │
│ - Connect        │ (ws://localhost:8765)
│ - Send File      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ WebSocket Server │
│ - Receive Data   │
│ - Validate       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Temp Storage     │
│ temp_uploads/    │
│ - Buffer Files   │
└────────┬─────────┘
         │
         │ Send to File Manager
         ▼
┌──────────────────┐
│ File Manager API │
│ /api/upload      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Final Storage    │
│ remote_uploads/  │
│ └── {username}/  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Database Update  │
│ - Store Metadata │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ File Manager UI  │
│ - Show in List   │
└──────────────────┘
```

---

## 📈 Roadmap & Mở rộng

### 🎯 Tính năng có thể thêm

```yaml
Phase 1 (Current):
  - ✅ User authentication & authorization
  - ✅ File upload/download/delete
  - ✅ Folder management
  - ✅ Recycle bin
  - ✅ File preview

Phase 2 (Future):
  - 🔄 File sharing & collaboration
  - 🔄 Version control
  - 🔄 Activity logging
  - 🔄 User management (Admin panel)
  - 🔄 File encryption

Phase 3 (Advanced):
  - 🔄 Cloud storage integration (AWS S3, Google Drive)
  - 🔄 API Rate limiting
  - 🔄 File compression
  - 🔄 Full-text search
  - 🔄 File versioning
```

### ⚡ Tối ưu hóa hiệu năng

| Tối ưu          | Hiện tại             | Tương lai                     |
| --------------- | -------------------- | ----------------------------- |
| 🗄️ Database     | SQLite (Single file) | PostgreSQL/MySQL (Multi-user) |
| 📦 Storage      | Local filesystem     | AWS S3 / Cloud Storage        |
| 🔄 Caching      | None                 | Redis cache layer             |
| 🌐 Distribution | Single server        | CDN + Load balancing          |
| 🗜️ Files        | Full size            | Compression + thumbnails      |
| 📊 Monitoring   | Basic logs           | ELK stack / Prometheus        |

---

## 📚 Các công nghệ sử dụng

### Backend

- **Framework**: Flask 2.0+ (Python web framework)
- **Real-time**: WebSockets (Python websockets library)
- **Database**: SQLite 3 (lightweight SQL database)
- **Authentication**: Session tokens + Password hashing (PBKDF2)

### Frontend

- **HTML5**: Semantic markup
- **CSS3**: Modern styling
- **JavaScript (ES6+)**: Upload logic, UI interaction
- **WebSocket API**: Real-time file transfer

### DevOps

- **Runtime**: Python 3.8+
- **Package Manager**: pip
- **Version Control**: Git

---

## 🤝 Đóng góp (Contributing)

Nếu bạn muốn đóng góp cho dự án:

1. **Fork** repository
2. **Tạo feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to branch** (`git push origin feature/AmazingFeature`)
5. **Tạo Pull Request**

### Code Style

- Tuân theo PEP 8 cho Python
- Sử dụng 4 spaces cho indentation
- Thêm docstrings cho functions
- Comment code phức tạp

---

## 📄 Giấy phép (License)

```
MIT License

Copyright (c) 2025 TransferFlow Hub - Nhóm 8

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

**Tóm tắt:**

- ✅ Sử dụng cho mục đích thương mại
- ✅ Sửa đổi code tùy ý
- ✅ Phân phối hoặc chia sẻ
- ❌ Không có warranty
- ❌ Không có liability

---

## 📞 Support & Contact

### 🆘 Khi gặp sự cố

1. **Xem FAQ**: Tìm kiếm câu hỏi thường gặp ở phần Troubleshooting
2. **Check Logs**: Xem terminal output để tìm lỗi
3. **Reset Database**: Xóa `.db` files và tạo lại
4. **Tạo Issue**: Báo cáo bug chi tiết trên GitHub

### 📧 Liên hệ

**Email:** support@transferflowhub.local
**GitHub:** https://github.com/yourusername/repo

### 📋 Template báo cáo lỗi

```markdown
## Lỗi: [Mô tả ngắn]

### Thông tin hệ thống

- OS: Windows 10 / Ubuntu 20.04 / etc
- Python: 3.8 / 3.9 / 3.10 / 3.11
- Browser: Chrome / Firefox / Edge

### Các bước để tái tạo

1. ...
2. ...
3. ...

### Kết quả mong đợi

...

### Kết quả thực tế

...

### Error message / Screenshots

[Paste error hoặc screenshot]
```

---

## 📚 Tài liệu bổ sung

- 📖 [Backend Documentation](backend/README.md)
- 📖 [Logging Configuration](backend/logging.md)
- 📖 [Multi-file Upload Guide](backend/MULTI_FILE_UPLOAD.MD)
- 📖 [Database Schema](docs/database.md) _(nếu có)_

---

## 🙌 Lời cảm ơn

- **Flask**: Web framework tuyệt vời
- **WebSockets**: Real-time communication
- **SQLite**: Lightweight database
- **Community**: Mọi người đã hỗ trợ dự án

---

## 📊 Project Statistics

```
Total Lines of Code: ~2000+
Languages:
  - Python: 65%
  - JavaScript: 20%
  - HTML/CSS: 15%

Development Time: ~2-3 weeks
Team Size: 6 members
```

---

<div align="center">

### ⭐ Nếu dự án hữu ích, hãy give a ⭐ Star!

Made with ❤️ by **Nhóm 8 - ĐHGTVT TP.HCM**

**Last Updated**: November 29, 2025

</div>
