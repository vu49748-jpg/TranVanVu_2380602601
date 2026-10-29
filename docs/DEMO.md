# Kịch bản demo và nghiệm thu

Đánh dấu đạt sau khi thực hiện thật. Test tự động không thay thế phần thiết bị và dịch vụ bên ngoài.

## Chuẩn bị

- API HTTPS đã live, PostgreSQL có dữ liệu, email gửi được.
- Điện thoại Android thật có GPS, camera và gia tốc kế; bật quyền Camera và vị trí chính xác.
- Có một màn hình thứ hai hiển thị QR: điện thoại admin hoặc Android emulator trên laptop. Nhân viên quét bằng điện thoại thật.
- Hai tài khoản: admin và nhân viên, email nhận OTP được.
- Giờ thiết bị chính xác, có Internet, không bật giả vị trí.

## Luồng kiểm tra

1. **Tên bài**: mở project `TranVanVu_2380602601`, chỉ ra Flutter `lib/`, tên APK/nhãn Android và MSSV.
2. **Đăng ký**: đăng ký nhân viên bằng email thật → nhận OTP → nhập sai thử một lần → nhập đúng → xác thực thành công.
3. **Đăng nhập**: tên đăng nhập + mật khẩu → Email OTP mới → nhân viên vào dashboard cá nhân.
4. **Phân quyền**: đăng xuất và đăng nhập admin bằng OTP → vào trang quản trị. Có thể dùng `/docs` chứng minh token nhân viên bị từ chối ở `/employees`.
5. **CRUD nhân viên**: thêm nhân viên tạm → xem danh sách → sửa tên/phòng ban → xóa bản ghi tạm. Nhân viên có lịch sử thì khóa thay vì xóa.
6. **CRUD điểm chấm công**: thêm điểm → dùng vị trí thật hoặc nhập tọa độ → sửa bán kính → xóa điểm tạm chưa có ca. Giữ lại một điểm để demo.
7. **CRUD ca và phân ca**: tạo ca bao phủ giờ demo hiện tại, gán điểm và phân cho nhân viên vào hôm nay. Thử phân ca trùng để thấy lỗi; sửa/xóa bản ghi tạm chưa có lịch sử.
8. **b — vị trí**: vào Chấm công, lấy GPS; kiểm tra tọa độ, sai số, khoảng cách. Nhấn mở bản đồ và chia sẻ qua bảng chia sẻ Android.
9. **d — chuyển động**: ở trang tổng quan mở Đo chuyển động. Giữ máy rồi di chuyển nhẹ, xem đồ thị, số mẫu và RMS sau 3 giây.
10. **e — QR**: admin mở QR của điểm chấm công trên màn hình thứ hai. Nhân viên quét bằng camera thật. Chụp lại QR cũ và đợi hết hạn để kiểm tra bị từ chối.
11. **Chấm công vào/ra**: lấy đủ dữ liệu và xác nhận vào. Ghi nhận giờ máy chủ, trạng thái và bằng chứng. Quét QR mới rồi ra ca. Thử gọi lại để thấy chống trùng.
12. **Giải trình có bằng chứng**: thử GPS ngoài phạm vi hoặc QR hết hạn, đọc rõ nguyên nhân, gửi giải trình kèm mẫu đã lấy. Chỉ đề xuất thời gian đã xảy ra.
13. **Duyệt**: admin xem hồ sơ, nhập nhận xét rồi duyệt/từ chối. Duyệt xong bảng công đổi trạng thái `Đã điều chỉnh`, yêu cầu không sửa/xóa tiếp được.
14. **Nhật ký & CSV**: admin xem ai đã thay đổi dữ liệu, thời gian và dữ liệu trước đó; xuất CSV mở được tiếng Việt.
15. **Bền vững & nhóm**: đóng/mở app, khởi động lại backend, dữ liệu vẫn còn trong PostgreSQL. Chạy source và APK trên máy khác với cùng API.

## Câu hỏi cần trả lời khi thuyết trình

- Thời gian chấm công lấy từ đâu? **Máy chủ**, không dùng giờ điện thoại để ghi giờ công.
- Vì sao cần mẫu GPS mới? Tránh dùng lại vị trí xem trước quá cũ; máy chủ kiểm tra tuổi mẫu và độ chính xác.
- QR có gì khác mã in cố định? Được ký, gắn điểm/phiên bản, hết hạn 90 giây, tự làm mới.
- Cảm biến có chứng minh đúng nhân viên không? Không. Đây là phép đo chuyển động và dữ liệu hỗ trợ xem xét tình huống; danh tính dùng tài khoản + mật khẩu + OTP.
- Tại sao có bản ghi không xóa được? Giữ lịch sử và quan hệ dữ liệu. Có thể thao tác CRUD đầy đủ trên bản ghi chưa bị tham chiếu.
- Tính năng mới? Xem [TINH_NANG_MOI.md](TINH_NANG_MOI.md), trình bày đúng phạm vi đối chiếu, không khẳng định toàn thế giới chưa có.
