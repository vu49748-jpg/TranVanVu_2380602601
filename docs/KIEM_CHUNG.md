# Trạng thái kiểm chứng

Ghi nhận trong phiên xây dựng ngày 29/10/2026. Chỉ đánh dấu đạt phần đã chạy thực tế.

| Phần | Kết quả |
|---|---|
| Flutter analyze | Đã chạy, không có vấn đề |
| Flutter tests | 6/6 test đã qua: địa chỉ HTTPS, giờ Việt Nam, đăng nhập/đăng ký, bố cục admin/nhân viên và hồi quy nhập 23:59 với locale vi khi nền tảng dùng giờ 12 tiếng |
| Backend API, gửi email và công cụ nghiệm thu | 26 test offline đã qua: 24 test API/email và 2 test dọn dữ liệu kiểm tra, bảo vệ dữ liệu có sẵn, không ghi mật khẩu/OTP/JWT vào báo cáo |
| Cầu nối Apps Script | Node kiểm tra HMAC, sửa payload, hết hạn, chèn nhiều người nhận, phát lại và gửi đồng thời; MailApp được mock, không gửi email thật |
| APK Android release | Bản release cuối đã build với URL Render công khai, sửa nhập giờ 24 tiếng và đổi nhãn bằng chứng thành “GPS và QR đạt kiểm tra”; nhãn `TranVanVu_2380602601`, package `vn.edu.tranvanvu.tranvanvu_2380602601`, min API 24, target API 36. Analyzer không có vấn đề |
| Cài và mở trên thiết bị | Đã cài bản có sửa giờ 24 tiếng và mở trên ASUS Android 13 cùng Pixel_7; các phiên đăng nhập được giữ nguyên. Trước đó đã kiểm tra mở màn đăng nhập trên ASUS, không có lỗi runtime trong log của app; bản release bổ sung nhãn GPS/QR chính xác đã build sau lượt kiểm thử này |
| Nhập giờ 24 tiếng trên giao diện thiết bị | Đã xác nhận trên APK mới của Pixel_7 khi thiết lập Android `time_12_24` là null, hệ thống dùng giờ 12 tiếng: nhập 23 và 58, xác nhận được, hộp thoại đóng và form hiện 23:58. Đã rời form mà KHÔNG LƯU; ca demo vẫn 08:00–23:59. Hồi quy tự động 23:59 cũng đã qua |
| Integration test trên thiết bị | Đã chạy lại sau khi mở khóa: 1 test qua trên ASUS Android 13, lấy mẫu gia tốc thật, hiển thị kết quả và đọc/ghi/xóa khóa thử trong secure storage |
| Apps Script HTTPS công khai | Đã kiểm tra URL /exec: trả đúng tên dịch vụ và ready; POST không có chữ ký bị từ chối. Kiểm tra này không gửi email |
| API chấm công HTTPS công khai | Đã kiểm tra https://tranvanvu-2380602601-api.onrender.com/health qua HTTPS: HTTP 200, đúng project, status ok, email_configured true; /docs và /openapi.json trả 200; /employees và /assignments khi chưa đăng nhập trả 401 |
| Đăng nhập admin bằng mật khẩu + Email OTP thật | Đã nhận OTP email thật và vào đúng Trang quản trị trên ASUS Android 13, sau đó cũng đăng nhập thành công trên Pixel_7 với cùng API Render công khai |
| Đăng ký nhân viên qua email | Người dùng xác nhận đã đăng ký và xác minh email thật thành công cho tài khoản `nhanvienvu` trên API công khai |
| Đăng nhập và phân quyền nhân viên | Đã quan sát `nhanvienvu` vào đúng dashboard NHÂN VIÊN trên ASUS, có nút Chấm công của mình và không có các menu quản trị |
| CRUD trên API production | Đã tạo, xem danh sách, sửa và xóa qua giao diện Flutter thật trên ASUS, dùng phiên admin với API Render: nhân viên tạm `NV_KIEM_TRA_CRUD` → `NV_KIEM_TRA_CRUD_SUA`, phòng ban `QA`; điểm `DIEM_KIEM_TRA_CRUD`, bán kính 150 → 175 m; ca `CA_KIEM_TRA_CRUD`, cho phép trễ 10 → 15 phút; phân ca đổi ngày 29/10/2026 → 30/10/2026. Đã xóa theo thứ tự phụ thuộc; số lượng phân ca 0, ca 0, điểm 0, nhân viên 1 là kết quả CUỐI ĐỢT CRUD TẠM, trước khi tạo dữ liệu demo, không phải tổng hiện tại. Admin ban đầu được giữ nguyên; không chạy CLI live |
| Dữ liệu demo đang giữ lại | Sau đợt CRUD tạm đã tạo điểm `DEMO VU` bằng GPS thật, ca `CA DEMO VU` và phân ca cho nhân viên đã xác minh. Ca riêng `CA KIEM THU GIAI TRINH` 06:00–07:00 được dùng để kiểm thử giải trình; dữ liệu demo có chủ đích được giữ lại. Không ghi tọa độ cá nhân hoặc thông tin đăng nhập trong tài liệu |
| Gia tốc trên máy thật | Đã qua integration test cảm biến thật trong 3 giây. Trên màn chấm công của bản release ASUS đã quan sát RMS 0.00 m/s² và 49 mẫu thật khi máy đứng yên; không dùng số liệu cảm biến giả |
| Chấm công vào bằng GPS và camera QR thật | Người dùng xác nhận chấm công vào thành công từ ASUS sau khi lấy GPS thật, quét QR hiển thị trên Pixel_7 và gửi đến API Render. Đã kiểm tra lịch sử ca `CA DEMO VU` ngày 29/10/2026, lịch 08:00–23:59, vào 18:21 và ra 18:28 (GMT+7), hiển thị 0.1 giờ công hoàn tất. Trạng thái Đi muộn đúng với thời điểm thực tế so với giờ bắt đầu ca demo |
| GPS và chia sẻ vị trí qua Android | Trên ASUS đã quan sát sai số GPS 13 m, khoảng cách đến điểm demo 3 m. Nhấn Chia sẻ vị trí mở đúng Android ChooserActivity; bản xem trước có liên kết Google Maps chứa vị trí thật. Đã đóng mà không chọn người nhận; xác nhận tạo link và mở bảng chia sẻ native, chưa gửi hoặc kiểm tra giao đến bên nhận. Không ghi tọa độ cá nhân trong tài liệu |
| Chấm công ra | Người dùng xác nhận đã nhấn chấm công ra; lịch sử thật trên ASUS đã ghi giờ ra 18:28 cho ca vào 18:21 ngày 29/10/2026, hiển thị 0.1 giờ công hoàn tất |
| Từ chối chấm công ngoài khung giờ | Đã thử thật trên ASUS với ca riêng `CA KIEM THU GIAI TRINH` ngày 29/10/2026, 06:00–07:00, sau khi quét QR bằng camera và lấy GPS/chuyển động; API từ chối đúng ngoài khung giờ (HTTP 400) |
| Từ chối chấm công riêng vì QR hết hạn | Chưa xác minh riêng trên production: đợt thử ca ban đầu kết thúc bằng chấm công ra thành công; ca kiểm thử 06:00–07:00 bị chặn ở điều kiện khung giờ trước khi kiểm tra QR. Các trường hợp QR hết hạn có kiểm thử backend offline |
| Giải trình kèm bằng chứng và sửa yêu cầu live | Từ màn chấm công bị từ chối, nhân viên đã gửi GPS/QR/chuyển động lên Render, xem yêu cầu Chờ duyệt rồi sửa để đề xuất giờ vào 06:00 và giờ ra 07:00. Bằng chứng được giữ lại sau sửa. Hồ sơ lúc lưu có cờ QR hết hạn; đây là phát hiện hết hạn khi LƯU GIẢI TRÌNH, không phải kết quả của kiểm thử âm endpoint chấm công |
| Admin xem và phê duyệt giải trình live | Admin trên Pixel_7 đã xem bằng chứng cùng metadata cảm biến và duyệt với nhận xét ghi rõ KIỂM THỬ; trạng thái chuyển Đã duyệt. Nhật ký “Duyệt điều chỉnh chấm công” có các trường `previous` và `correction_id`. ASUS tải mới lịch sử thấy ca kiểm thử 06:00–07:00 Đã điều chỉnh và ca chấm công thật 18:21–18:28 không đổi. Luồng chấp thuận đã qua; không coi đây là xác nhận đã thử mọi nhánh từ chối |
| PostgreSQL sau deploy/restart | /health đã thực hiện SELECT 1 thành công trên database của API production; việc giữ dữ liệu qua restart vẫn cần kiểm thử |
| Các thành viên cùng chạy | Đã chạy trên ASUS và emulator Pixel_7 của phiên kiểm thử. Người dùng xác nhận hiện chưa có thêm Android của thành viên khác, sẽ nhờ kiểm thử sau; mục tất cả thành viên cùng chạy vẫn chờ xác nhận |
| Tính mới | Có source và tài liệu đối chiếu; tính mới cuối cùng cần giảng viên đánh giá |

Các luồng chính nêu trên đã có nghiệm thu bằng thiết bị thật và API production, ngoài các kiểm thử tự động. Những mục chưa xác minh vẫn được ghi rõ; không khẳng định tính mới toàn thị trường hoặc bảo đảm điểm số. Đối chiếu [DEMO.md](DEMO.md) để chạy lại đúng dữ liệu và điều kiện.
