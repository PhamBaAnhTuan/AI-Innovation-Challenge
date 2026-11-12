# AI Innovation Challenge

## Chạy trang đăng ký trên máy local

1. Cài Python và cài dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Tạo database trên Neon, sao chép connection string PostgreSQL trong mục **Connect** của Neon, sau đó thêm các biến sau vào file `.env` ở thư mục gốc dự án (nếu file đã tồn tại, chỉ thêm hoặc cập nhật các biến tương ứng):

   ```dotenv
   DATABASE_URL="postgresql://USER:PASSWORD@HOST/DB?sslmode=require"
   ADMIN_USERNAME="your-admin-name"
   ADMIN_PASSWORD="use-a-long-unique-password"
   SESSION_SECRET="a-long-random-secret"
   ```

   Thay giá trị ví dụ bằng connection string Neon thực tế và thông tin quản trị riêng. Tạo `SESSION_SECRET` ngẫu nhiên bằng `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Giữ nguyên `sslmode=require` nếu URL Neon cung cấp có tham số này. Không commit hoặc chia sẻ file `.env`.

3. Mở terminal tích hợp trong VS Code, chuyển tới thư mục dự án và chạy `.\start.bat`. FastAPI chạy nền trong cùng terminal, Vite chạy ở foreground; log của cả hai hiển thị trong terminal này. Nhấn `Ctrl+C` để dừng. Đảm bảo đã tạo `.venv`, cài `requirements.txt`, chạy `npm install` và cấu hình `.env` trước khi khởi chạy.

   Hoặc tự mở hai terminal:

   ```powershell
   python -m uvicorn server:app --reload
   ```

   ```powershell
   npm run dev
   ```

Mở URL Vite hiển thị trong terminal. Proxy chuyển các request `/api`, `/admin`, `/admin.js` và `/admin.css` tới FastAPI. API kết nối PostgreSQL trên Neon qua `DATABASE_URL` và tự tạo bảng `registrations` khi khởi động lần đầu. Dữ liệu SQLite từ phiên bản trước không được tự động chuyển sang Neon.

Trang quản trị ở `/admin` (cũng có liên kết nhỏ cạnh dòng bản quyền) yêu cầu đăng nhập bằng `ADMIN_USERNAME` và `ADMIN_PASSWORD`. Quản trị viên xem danh sách, đánh dấu trạng thái nộp hồ sơ bản mềm và xuất Excel. Phiên đăng nhập được giới hạn thời gian; API quản trị yêu cầu CSRF token và khóa đăng nhập sai tạm thời. Trước khi triển khai công khai, hãy thay tài khoản/mật khẩu mẫu bằng mật khẩu mạnh riêng, đặt `SESSION_SECRET` ổn định và bật `SESSION_HTTPS_ONLY=true` khi chạy sau HTTPS. Không dựa vào đường dẫn khó đoán để bảo vệ trang quản trị.

## Triển khai

Frontend, `/admin`, `/admin.js`, `/admin.css` và `/api` cần được phục vụ cùng một origin. Build frontend bằng `npm run build`, thiết lập `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SESSION_SECRET` và `SESSION_HTTPS_ONLY=true` trong môi trường triển khai, chạy FastAPI bằng Uvicorn, sau đó cấu hình web server/reverse proxy phục vụ thư mục `dist` và chuyển tiếp các đường dẫn quản trị cùng `/api` tới FastAPI. Giới hạn quyền truy cập database vì nó chứa thông tin sinh viên.
