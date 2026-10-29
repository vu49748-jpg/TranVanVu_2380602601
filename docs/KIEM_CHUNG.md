# Trạng thái kiểm chứng

Ghi nhận trong phiên xây dựng ngày 29/10/2026. Chỉ đánh dấu đạt phần đã chạy thực tế.

| Phần | Kết quả |
|---|---|
| Flutter analyze | Đã chạy, không có vấn đề |
| Flutter tests | 5 test đã qua: địa chỉ HTTPS, giờ Việt Nam, đăng nhập/đăng ký và bố cục admin/nhân viên |
| Backend API, gửi email và công cụ nghiệm thu | 26 test offline đã qua: 24 test API/email và 2 test dọn dữ liệu kiểm tra, bảo vệ dữ liệu có sẵn, không ghi mật khẩu/OTP/JWT vào báo cáo |
| Cầu nối Apps Script | Node kiểm tra HMAC, sửa payload, hết hạn, chèn nhiều người nhận, phát lại và gửi đồng thời; MailApp được mock, không gửi email thật |
| APK Android release | Đã build lại với URL API Render công khai; nhãn `TranVanVu_2380602601`, package `vn.edu.tranvanvu.tranvanvu_2380602601`, min API 24, target API 36 |
| Cài và mở trên điện thoại | Đã cài APK dùng API công khai lên ASUS Android 13, mở đúng màn hình đăng nhập và không có lỗi runtime trong log của app |
| Integration test trên thiết bị | Đã chạy lại sau khi mở khóa: 1 test qua trên ASUS Android 13, lấy mẫu gia tốc thật, hiển thị kết quả và đọc/ghi/xóa khóa thử trong secure storage |
| Apps Script HTTPS công khai | Đã kiểm tra URL /exec: trả đúng tên dịch vụ và ready; POST không có chữ ký bị từ chối. Kiểm tra này không gửi email |
| API chấm công HTTPS công khai | Đã kiểm tra https://tranvanvu-2380602601-api.onrender.com/health qua HTTPS: HTTP 200, đúng project, status ok, email_configured true; /docs và /openapi.json trả 200; /employees và /assignments khi chưa đăng nhập trả 401 |
| Gửi/nhận OTP thật | Apps Script và Render đã cấu hình; cần thử đăng nhập để xác nhận gửi/nhận email thật. Cờ email_configured không chứng minh việc gửi thành công |
| Gia tốc trên máy thật | Đã qua integration test bằng cảm biến thật |
| GPS và camera quét QR trên máy thật | Cần kiểm thử luồng đầy đủ sau khi API được deploy |
| PostgreSQL sau deploy/restart | /health đã thực hiện SELECT 1 thành công trên database của API production; việc giữ dữ liệu qua restart vẫn cần kiểm thử |
| Các thành viên cùng chạy | Cần chạy trên máy/điện thoại thành viên khác |
| Tính mới | Có source và tài liệu đối chiếu; tính mới cuối cùng cần giảng viên đánh giá |

Chưa coi bài là hoàn tất nghiệm thu chỉ vì test tự động qua. Đối chiếu tiếp [DEMO.md](DEMO.md).
