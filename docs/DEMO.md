# Kịch bản demo và nghiệm thu

Đánh dấu đạt sau khi thực hiện thật. Test tự động không thay thế phần thiết bị và dịch vụ bên ngoài.

## Chuẩn bị

- API HTTPS đã live, PostgreSQL có dữ liệu, email gửi được.
- Điện thoại Android thật có GPS, camera và gia tốc kế; bật quyền Camera và vị trí chính xác.
- Có một màn hình thứ hai hiển thị QR: điện thoại admin hoặc Android emulator trên laptop. Nhân viên quét bằng điện thoại thật.
- Hai tài khoản: admin và nhân viên, email nhận OTP được.
- Giờ thiết bị chính xác, có Internet, không bật giả vị trí.

## Dữ liệu đã kiểm thử ngày 29/10/2026

- Điểm `DEMO VU` được khai báo bằng GPS thật; tài khoản nhân viên `nhanvienvu` đã xác minh email và vào đúng dashboard nhân viên.
- `CA DEMO VU` có lịch 08:00–23:59, đã chấm công thật trên ASUS vào 18:21 và ra 18:28 (GMT+7), hiển thị 0.1 giờ công. Đi muộn là đúng vì giờ vào thực tế sau giờ bắt đầu ca demo.
- `CA KIEM THU GIAI TRINH` 06:00–07:00 là ca kiểm thử riêng, không trùng ca trên. Chấm công ngoài khung giờ đã bị từ chối; nhân viên gửi/sửa giải trình kèm GPS/QR/chuyển động, admin xem và duyệt với nhận xét KIỂM THỬ. Lịch sử ghi Đã điều chỉnh 06:00–07:00 cho ca thử; bản ghi thật 18:21–18:28 không thay đổi. Không mô tả giờ đề xuất của ca thử là thời gian làm việc thực tế buổi sáng.
- Bản APK cuối gồm sửa nhập giờ 24 tiếng và nhãn **GPS và QR đạt kiểm tra**. Nhãn này không có nghĩa mọi điều kiện của ca đều đã đạt. Kết quả đã chạy: 6 widget test, 26 backend test offline và 1 integration test cảm biến/secure storage thật; analyzer không có vấn đề.

**Quy tắc demo lại:** ca đã có giờ ra không chấm công lại được. Admin cần phân ca cho ngày mới hoặc nhân viên khác với khung giờ phù hợp lúc demo; nếu chọn ngày mới thì chạy trong ngày/khung giờ đó. Kiểm tra không trùng lịch. Giữ các cơ chế chống trùng, kiểm tra thời gian và lịch sử thật; không reset giờ công hoặc tắt bảo vệ để làm lại demo.

Chia sẻ vị trí đã mở đúng bảng chia sẻ Android với link bản đồ thật trong preview, rồi đóng mà không chọn người nhận. Chưa thử giao link cho người nhận bên ngoài. Việc giữ dữ liệu sau restart backend và chạy trên Android của mọi thành viên vẫn cần xác nhận; người dùng hiện chưa có thêm thiết bị thành viên để thử.

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
10. **e — QR**: admin mở QR của điểm chấm công trên màn hình thứ hai; nhân viên quét bằng camera thật. Nếu kiểm thử QR hết hạn, dùng ca còn mở và đang trong khung giờ hợp lệ, giữ QR đã quét quá 90 giây rồi gửi để kiểm tra đúng nguyên nhân QR. Kiểm thử âm riêng này chưa được xác minh live trong phiên hiện tại; test backend offline đã có. Cờ QR hết hạn trong hồ sơ giải trình không thay thế kiểm thử này.
11. **Chấm công vào/ra**: lấy đủ dữ liệu và xác nhận vào. Ghi nhận giờ máy chủ, trạng thái và bằng chứng. Quét QR mới rồi ra ca. Thử gọi lại để thấy chống trùng.
12. **Giải trình có bằng chứng**: luồng đã kiểm thử dùng ca riêng ngoài khung giờ, đọc thông báo từ chối rồi gửi giải trình kèm mẫu GPS/QR/chuyển động đã lấy. Xem trạng thái Chờ duyệt, sửa giờ đề xuất và kiểm tra bằng chứng còn được giữ. Máy chủ đánh giá lại bằng chứng lúc lưu nên QR có thể đã hết hạn tại thời điểm này. Chỉ đề xuất thời gian đã xảy ra; ca thử phải có tên và lý do ghi rõ KIỂM THỬ.
13. **Duyệt**: admin xem hồ sơ và metadata cảm biến, nhập nhận xét rồi duyệt/từ chối. Luồng chấp thuận đã được kiểm thử live: yêu cầu Đã duyệt, ca thử Đã điều chỉnh; nhân viên tải lại bảng công và kiểm tra ca thật ban đầu không đổi. Không khẳng định đã kiểm thử live mọi nhánh từ chối chỉ từ kết quả chấp thuận.
14. **Nhật ký & CSV**: admin xem ai đã thay đổi dữ liệu, thời gian và dữ liệu trước đó; xuất CSV mở được tiếng Việt.
15. **Bền vững & nhóm**: đóng/mở app, khởi động lại backend, dữ liệu vẫn còn trong PostgreSQL. Chạy source và APK trên máy khác với cùng API.

## Câu hỏi cần trả lời khi thuyết trình

- Thời gian chấm công lấy từ đâu? **Máy chủ**, không dùng giờ điện thoại để ghi giờ công.
- Vì sao cần mẫu GPS mới? Tránh dùng lại vị trí xem trước quá cũ; máy chủ kiểm tra tuổi mẫu và độ chính xác.
- QR có gì khác mã in cố định? Được ký, gắn điểm/phiên bản, hết hạn 90 giây, tự làm mới.
- Cảm biến có chứng minh đúng nhân viên không? Không. Đây là phép đo chuyển động và dữ liệu hỗ trợ xem xét tình huống; danh tính dùng tài khoản + mật khẩu + OTP.
- Vì sao GPS và QR đạt mà vẫn không chấm công được? Ca còn có điều kiện thời gian, chủ sở hữu và chống trùng. Nhãn bằng chứng chỉ nói về GPS/QR; ca kiểm thử ngoài khung giờ đã chứng minh điều này.
- Tại sao có bản ghi không xóa được? Giữ lịch sử và quan hệ dữ liệu. Có thể thao tác CRUD đầy đủ trên bản ghi chưa bị tham chiếu.
- Tính năng mới? Xem [TINH_NANG_MOI.md](TINH_NANG_MOI.md), trình bày đúng phạm vi đối chiếu, không khẳng định toàn thế giới chưa có.
