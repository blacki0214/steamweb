@echo off
:: Chuyển đúng ổ đĩa và thư mục
cd /d D:\secret\steamweb\data-pipeline

:: Kích hoạt môi trường ảo (Virtual Env)
call ..\.venv\Scripts\activate.bat

:: Chạy script hàng ngày
python -m jobs.run_daily_update

:: (Tuỳ chọn) Đổi lại thành python -m jobs.run_ingest_all nếu bạn muốn chạy file cập nhật Steam
