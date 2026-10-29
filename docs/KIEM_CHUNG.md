# Trạng thái kiểm chứng

Ghi nhận trong phiên xây dựng ngày 29/10/2026. Chỉ đánh dấu đạt phần đã chạy thực tế.

| Phần | Kết quả |
|---|---|
| Flutter analyze | Đã chạy, không có vấn đề |
| Flutter tests | 5 test đã qua: địa chỉ HTTPS, giờ Việt Nam, đăng nhập/đăng ký và bố cục admin/nhân viên |
| Backend API và gửi email | 24 test đã qua; test dùng SQLite tạm và mock dịch vụ email |
| Cầu nối Apps Script | Node kiểm tra HMAC, sửa payload, hết hạn, chèn nhiều người nhận và phát lại; MailApp được mock, không gửi email thật |
| APK Android release | Build thành công, nhãn `TranVanVu_2380602601`, package `vn.edu.tranvanvu.tranvanvu_2380602601`, min API 24, target API 36 |
| Cài trên điện thoại | Đã cài APK release thành công lên ASUS Android 13; kiểm tra giao diện tiếp sau khi mở khóa màn hình |
| Integration test trên thiết bị | Lần thử đầu chưa hoàn tất vì kết nối debug đóng; thiết bị đang khóa. Cần mở khóa và chạy lại trước khi xác nhận cảm biến đạt |
| API HTTPS công khai | Chờ tài khoản Render và cấu hình deploy |
| Gửi/nhận OTP thật | Chờ deploy Apps Script và cấu hình khóa ở Render |
| GPS/camera/gia tốc trên máy thật | Cần chạy và xác nhận trên thiết bị |
| PostgreSQL sau deploy/restart | Cần kiểm thử trên máy chủ đã deploy |
| Các thành viên cùng chạy | Cần chạy trên máy/điện thoại thành viên khác |
| Tính mới | Có source và tài liệu đối chiếu; tính mới cuối cùng cần giảng viên đánh giá |

Chưa coi bài là hoàn tất nghiệm thu chỉ vì test tự động qua. Đối chiếu tiếp [DEMO.md](DEMO.md).
