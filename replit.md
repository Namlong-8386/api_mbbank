# MBBank API

Dự án đã gộp thành một ứng dụng Python duy nhất, bao gồm cả:

- Giải captcha MBBank bằng model TensorFlow/Keras (`model_mb.h5` + `model_mb.json`)
- Tự động hóa đăng nhập/truy vấn lịch sử MBBank qua Playwright

## Chạy trên Replit

Workflow `Start application` chạy `python run.py`. Server lắng nghe trên cổng 5000 (hoặc cổng được chỉ định qua biến môi trường `PORT`).

## Cấu hình bắt buộc

Thêm các secret sau trong Replit (không để trực tiếp trong code):

- `MB_PHONE` — Số điện thoại đăng nhập MBBank
- `MB_PASSWORD` — Mật khẩu đăng nhập MBBank
- `MB_STK` — Số tài khoản MBBank cần truy vấn

## API endpoints

- `GET /` — Danh sách endpoint
- `POST /api/captcha/mbbank` — Giải captcha từ base64
  - Body: `{"base64": "..."}`
  - Trả về: `{"status": "success", "captcha": "..."}`
- `GET /api/status` — Trạng thái đăng nhập
- `GET /api/login` — Đăng nhập MBBank
- `GET /api/history` — Lấy lịch sử giao dịch (tự động login nếu cần, cache 30 giây)
  - Thêm `?refresh=1` hoặc body `{"refresh": 1}` để bỏ qua cache.
- `GET /api/history/refresh` — Lấy lịch sử mới nhất, luôn bỏ qua cache.

## Lưu ý

- Captcha được giải hoàn toàn offline bằng model local, không còn gọi API thuê bên ngoài như file `apimbbank.js` cũ.
- File `apimbbank.js` đã được lưu lại dưới tên `apimbbank.js.bak` để tham khảo nếu cần.
- Model Keras 2 cũ (`model_mb.json` + `model_mb.h5`) được load qua gói `tf_keras` thay vì `keras` 3, để tương thích với TensorFlow 2.21+ trên Python 3.12.
