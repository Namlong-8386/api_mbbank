# MBBank API

Dự án đã gộp thành một ứng dụng Python duy nhất, bao gồm cả:

- Giải captcha MBBank bằng model TensorFlow/Keras (`model_mb.h5` + `model_mb.json`)
- Tự động hóa đăng nhập/truy vấn lịch sử MBBank qua Playwright

## Chạy trên Replit

Workflow `Start application` chạy `python run.py`. Server lắng nghe trên cổng 5000 (hoặc cổng được chỉ định qua biến môi trường `PORT`).

## Cấu hình bắt buộc

Có 2 cách nhập thông tin đăng nhập. **Cách 1 (Replit Secrets) an toàn hơn** và đã được cấu hình sẵn.

### Cách 1: Replit Secrets (khuyên dùng)

Thêm các secret trong tab **Tools → Secrets**:

- `MB_PHONE` — Số điện thoại đăng nhập MBBank
- `MB_PASSWORD` — Mật khẩu đăng nhập MBBank
- `MB_STK` — Số tài khoản MBBank cần truy vấn

### Cách 2: File `.env`

App đã hỗ trợ đọc từ file `.env`. Tuy nhiên Replit không cho phép AI tạo file `.env` chứa credential, nên bạn cần tự tạo:

1. Copy file `.env.example` thành `.env`.
2. Sửa các giá trị:

```env
MB_PHONE=098xxxxxxx
MB_PASSWORD=matkhau
MB_STK=so_tai_khoan
```

File `.env` đã được thêm vào `.gitignore` nên không bị commit.

## API endpoints

- `GET /` — Danh sách endpoint
- `POST /api/captcha/mbbank` — Giải captcha từ base64
  - Body: `{"base64": "..."}`
  - Trả về: `{"status": "success", "captcha": "..."}`
- `GET /api/status` — Trạng thái đăng nhập
- `GET /api/login` — Đăng nhập MBBank
- `GET /api/history` — Lấy lịch sử giao dịch (tự động login nếu cần, cache 30 giây)
- `POST /api/history` — Lấy lịch sử giao dịch, cho phép gửi credentials qua body
  - Body: `{"phone": "...", "password": "...", "stk": "..."}`

## Script Python sẵn có

- `python client.py` — Nhập credentials và gọi API lịch sử (yêu cầu server đang chạy).
- `python get_history.py` — Nhập credentials, tự khởi động server nếu chưa chạy, rồi lấy lịch sử.

## Lưu ý

- Captcha được giải hoàn toàn offline bằng model local, không còn gọi API thuê bên ngoài như file `apimbbank.js` cũ.
- File `apimbbank.js` đã được lưu lại dưới tên `apimbbank.js.bak` để tham khảo nếu cần.
- Model Keras 2 cũ (`model_mb.json` + `model_mb.h5`) được load qua gói `tf_keras` thay vì `keras` 3, để tương thích với TensorFlow 2.21+ trên Python 3.12.
