# Hướng dẫn: Multi-File Upload & Folder Upload

## Mục lục

- [Tổng quan](#tổng-quan)
- [Tính năng nổi bật](#tính-năng-nổi-bật)
- [Sử dụng (ví dụ)](#sử-dụng-ví-dụ)
- [Tùy chọn dòng lệnh](#tùy-chọn-dòng-lệnh)
- [Ví dụ thực tế](#ví-dụ-thực-tế)
- [Tối ưu hiệu suất](#tối-ưu-hiệu-suất)
- [Xử lý lỗi & Khôi phục](#xử-lý-lỗi--khôi-phục)
- [Logging & Monitoring](#logging--monitoring)
- [Khắc phục sự cố](#khắc-phục-sự-cố)
- [Best Practices](#best-practices)

## Tổng quan

TransferFlow Hub đã được nâng cấp để hỗ trợ:

- Upload nhiều file cùng lúc (multi-file upload)
- Upload toàn bộ thư mục (folder upload) và duyệt đệ quy
- Kiểm soát concurrency, theo dõi tiến trình, và xử lý lỗi/retry

## Tính năng nổi bật

- Multi-File Upload

  - Upload nhiều file đồng thời
  - Giới hạn concurrency để tối ưu hiệu suất
  - Theo dõi tiến trình cho từng file
  - Retry logic cho các lỗi mạng tạm thời

- Folder Upload

  - Upload toàn bộ folder, hỗ trợ duyệt đệ quy (subfolders)
  - Tự động scan và thu thập file
  - Loại bỏ file trùng lặp

- Concurrency Control
  - Giới hạn số upload đồng thời
  - Sử dụng semaphore/throttling để tối ưu băng thông

## Sử dụng (ví dụ)

Upload các file cụ thể:

```powershell
# Upload 3 file cụ thể
python app.py --mode client --file file1.txt file2.pdf file3.jpg

# Tăng concurrency
python app.py --mode client --file file1.txt file2.pdf file3.jpg --concurrency 5

# Tùy chỉnh kích thước chunk (bytes)
python app.py --mode client --file file1.txt file2.pdf --chunk 128000
```

Upload folder:

```powershell
# Upload folder (không duyệt subfolder)
python app.py --mode client --dir ./documents

# Upload folder với duyệt đệ quy
python app.py --mode client --dir ./documents --recursive

# Upload nhiều folder cùng lúc
python app.py --mode client --dir ./documents ./images ./videos

# Folder upload với concurrency cao
python app.py --mode client --dir ./documents --concurrency 8
```

Kết hợp files và folders:

```powershell
python app.py --mode client \
  --file important.txt backup.pdf \
  --dir ./documents ./images \
  --recursive

# Ghi log chi tiết
python app.py --mode client \
  --file file1.txt file2.txt \
  --dir ./folder1 ./folder2 \
  --log-level DEBUG \
  --log-file upload.log
```

Chạy cả server và client (local):

```powershell
python app.py --mode both \
  --dir ./uploads \
  --recursive \
  --concurrency 4

# Chạy server trên host/port tùy chỉnh
python app.py --mode both \
  --host 0.0.0.0 \
  --port 8766 \
  --file file1.txt file2.txt \
  --dir ./documents
```

## Tùy chọn dòng lệnh

- `--file PATH [PATH ...]` : Chỉ định file cụ thể để upload
- `--dir PATH [PATH ...]` : Chỉ định folder để upload
- `--recursive` : Duyệt đệ quy subfolders khi upload folder
- `--concurrency N` : Số upload đồng thời (mặc định: 2)
- `--chunk SIZE` : Kích thước chunk (bytes), mặc định ~64KB
- `--interactive` : Chế độ interactive (hỗ trợ single file)
- `--host HOST` : Host cho server (mặc định: localhost)
- `--port PORT` : Port cho server (mặc định: 8765)
- `--ws URL` : WebSocket URL cho client
- `--log-level LEVEL` : Log level (DEBUG, INFO, WARNING, ERROR)
- `--log-file PATH` : Ghi log ra file

## Ví dụ thực tế

Upload toàn bộ project (có subfolder):

```powershell
python app.py --mode client \
  --dir ./my-project \
  --recursive \
  --concurrency 6 \
  --log-level INFO
```

Backup nhiều folder:

```powershell
python app.py --mode client \
  --dir ./documents ./images ./videos \
  --recursive \
  --concurrency 4 \
  --log-file backup.log
```

Upload tới server remote qua WebSocket:

```powershell
python app.py --mode client \
  --ws ws://192.168.1.100:8765/ws \
  --file important.txt backup.pdf \
  --dir ./documents \
  --concurrency 8
```

## Tối ưu hiệu suất

- Concurrency Optimization

  - Network tốt: `--concurrency 8-16`
  - Network chậm: `--concurrency 2-4`
  - Server yếu: giới hạn `--concurrency 2-4`

- Chunk Size

  - File nhỏ: `--chunk 32768` (32KB)
  - File lớn: `--chunk 131072` (128KB)
  - Network chậm: giảm chunk (ví dụ 32768)

- Memory Usage
  - Mỗi upload đồng thời ~1-2MB RAM
  - Với nhiều file (ví dụ 1000 file) cân nhắc giảm concurrency

## Xử lý lỗi & Khôi phục

Common issues:

1. File không tồn tại: sẽ được bỏ qua (skip) và ghi warning
2. Permission denied: bỏ qua và ghi error
3. Network timeout: tự động retry (theo policy)
4. Disk full: dừng và ghi lỗi

Recovery:

- Quy trình tiếp tục với các file còn lại
- Các file thất bại được liệt kê trong bản tóm tắt (summary)
- Hỗ trợ retry riêng cho các file failed

## Logging & Monitoring

Ví dụ log:

```text
[14:30:15] app - INFO: Starting multi-file upload: 150 files
[14:30:16] client - INFO: Progress: 5/150 files completed (3.3%)
[14:30:17] client - INFO: Progress: 12/150 files completed (8.0%)
[14:30:18] client - INFO: Progress: 25/150 files completed (16.7%)
...
[14:35:20] client - INFO: Batch upload completed: 148/150 files successful
[14:35:20] client - WARNING: Failed files (2):
  - /path/to/corrupted/file1.txt
  - /path/to/permission/file2.pdf
```

Performance metrics để theo dõi:

- Tổng thời gian upload
- Tốc độ trung bình
- Success rate và danh sách failed files

## Khắc phục sự cố

- Upload chậm: tăng `--concurrency` hoặc giảm `--chunk`
- Memory issues: giảm `--concurrency`, kiểm tra RAM
- Network errors: kiểm tra WebSocket, giảm concurrency, tăng timeout

## Best Practices

1. Test với ít file trước (5–10 file)
2. Giám sát tài nguyên (CPU, RAM, network)
3. Chọn concurrency phù hợp với băng thông và sức mạnh server
4. Ghi log (sử dụng `--log-file`) cho môi trường production
5. Thiết kế recovery/ retry cho các file thất bại
