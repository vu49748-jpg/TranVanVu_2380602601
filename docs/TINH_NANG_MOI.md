# Đề xuất: hồ sơ giải trình chấm công theo ngữ cảnh cảm biến

## Vấn đề

Nhân viên có thể bị từ chối vì sai số GPS trong nhà hoặc QR đã hết hạn. Chỉ một thông báo “không chấm công được” khiến việc giải thích lại cho quản trị viên mất dữ liệu hoàn cảnh.

## Cách project giải quyết

Ứng dụng hiển thị báo cáo điều kiện từ backend khi chấm công bị từ chối: khoảng cách đến nơi làm, sai số GPS, thời điểm mẫu, cờ mock của Android, QR hợp lệ hay không, RMS và số mẫu gia tốc trong khoảng 3 giây.

Nhân viên có thể tạo yêu cầu, đính kèm mẫu đã lấy và đề xuất giờ vào/ra thực tế. Máy chủ kiểm tra lại bằng chứng tại lúc gửi giải trình; dữ liệu này không được mô tả là bằng chứng đã xác thực tại một thời điểm trong quá khứ. Admin đọc dữ liệu có cấu trúc, nhập nhận xét rồi quyết định. Việc duyệt lưu bản ghi công trước thay đổi, người duyệt và yêu cầu liên quan trong nhật ký.

Điểm tự đề xuất tập trung vào **hồ sơ giải trình kết hợp GPS + QR + mẫu chuyển động có số liệu và giải thích nguyên nhân**, đi kèm quy trình duyệt truy vết được.

## Đối chiếu tài liệu công khai ngày 29/10/2026

| Sản phẩm | Chức năng được tài liệu mô tả | Phạm vi khác biệt đề xuất trong bài |
|---|---|---|
| MISA AMIS Chấm công | GPS theo bán kính, phê duyệt và hình thức xác thực thay thế | Bài tự triển khai hồ sơ có mẫu gia tốc RMS/số mẫu và trạng thái QR cùng lý do GPS |
| Tanca | GPS, QR và các cảnh báo bất thường trong chấm công | Bài hiển thị mẫu chuyển động 3 giây và kết hợp vào hồ sơ giải trình có nhật ký điều chỉnh |

Nguồn: [MISA: chấm công xác thực bằng GPS](https://helpamis.misa.vn/amis-cham-cong/kb/cham-cong-xac-thuc-bang-dinh-vi-gps/), [Tanca: chức năng chấm công](https://tanca.io/feature/attendance).

Hai tài liệu được đối chiếu không mô tả chính xác toàn bộ quy trình hồ sơ cảm biến nêu trên. Đây là **nhận định từ tài liệu đã xem**, không chứng minh sản phẩm thực tế hay mọi app trên thị trường đều chưa có. Cần trình bày đề xuất với giảng viên để chốt tiêu chí 1 điểm tính năng mới; không hứa chắc điểm.

## Giới hạn kỹ thuật cần nói đúng

- GPS/cảm biến gửi từ máy khách không phải xác thực phần cứng. Thiết bị bị can thiệp vẫn có thể làm giả dữ liệu.
- Chuyển động không xác minh người cầm máy; không gọi đây là nhận diện danh tính hay chống chấm công hộ tuyệt đối.
- Không dùng QR sai/hết hạn hoặc GPS sai để tự cấp công; nhân viên phải gửi đề nghị, admin quyết định.
- Có thể gửi giải trình thủ công khi không thu được cảm biến; UI ghi rõ không có mẫu đính kèm.
