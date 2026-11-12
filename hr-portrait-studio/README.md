# HR Portrait Studio

Website thử nghiệm để tải ảnh chân dung, chọn trang phục THACO hoặc sơ mi trắng, tạo nền trắng và ảnh tỷ lệ 3:4.

## Tính năng
- Tải tối đa 20 ảnh mỗi lượt; JPG, PNG, WEBP; giới hạn mặc định 10 MB/ảnh.
- Xử lý từng ảnh độc lập, không trộn nhiều người vào cùng một yêu cầu.
- Hai mẫu trang phục:
  - **THACO:** áo sơ mi vàng kem nhạt, viền xanh ở mặt trong cổ áo, biểu tượng chữ `i` màu xanh nhỏ ở ngực trái.
  - **Sơ mi trắng:** áo sơ mi trắng dài tay, cổ bẻ hơi mở, nút trắng; không logo, cà vạt hoặc vest.
- Nền trắng, ảnh 3 × 4 cm (354 × 472 pixel, 300 DPI).
- Xem ảnh gốc và ảnh kết quả cạnh nhau; tải từng ảnh hoặc ZIP.
- Ảnh được xử lý trong bộ nhớ; backend không ghi ảnh tải lên ra đĩa.

## Chạy local trên Windows

```powershell
cd hr-portrait-studio
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Điền `OPENAI_API_KEY` trong `.env`, sau đó mở `http://localhost:8000`.

## Deploy Docker

```bash
docker build -t hr-portrait-studio .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="YOUR_API_KEY" \
  -e APP_ACCESS_PASSWORD="YOUR_SHARED_PASSWORD" \
  hr-portrait-studio
```

Đặt `OPENAI_API_KEY` và `APP_ACCESS_PASSWORD` trong Secrets/Environment của nền tảng hosting. Không commit `.env` và không đặt API key trong mã frontend. Có thể deploy Docker lên Render, Railway hoặc Replit.

## Lưu ý
- Mỗi ảnh tạo ra một lần gọi OpenAI Image Edits API, có thể phát sinh phí API. Organization có thể cần xác minh để sử dụng GPT Image.
- AI không thể cam kết giữ khuôn mặt giống tuyệt đối trong mọi ảnh. Luôn kiểm tra ảnh kết quả trước khi dùng cho hồ sơ chính thức.
- Logo nhỏ trên áo THACO được mô tả theo ảnh mẫu (biểu tượng chữ `i` xanh); không đảm bảo tái tạo chính xác như logo vector gốc.
- Khi public website, hãy đặt mật khẩu truy cập chung bằng `APP_ACCESS_PASSWORD`.
