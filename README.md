# TranVanVu_2380602601

Ứng dụng **chấm công nhân viên** — Trần Văn Vũ, MSSV **2380602601**, **nhóm 7**.

Ứng dụng di động viết bằng **Flutter**, dành cho **Android**. Backend **FastAPI + PostgreSQL**. Chọn ba mục **b: chia sẻ vị trí**, **d: đo chuyển động**, **e: quét QR**.

## Trạng thái trước khi nộp

Source đã triển khai các chức năng bên dưới. Bài chỉ sẵn sàng nộp sau khi hoàn tất **deploy API HTTPS**, **gửi/nhận Email OTP thật** và **kiểm thử GPS/camera/cảm biến trên điện thoại thật**. Xem [hướng dẫn deploy](docs/DEPLOY.md) và [kịch bản nghiệm thu](docs/DEMO.md).

Không có mật khẩu/OTP demo, không trả OTP về app, không dùng endpoint localhost trong ứng dụng. App mặc định kết nối API đã deploy tại `https://tranvanvu-2380602601-api.onrender.com`; có thể thay máy chủ trong phần thiết lập kết nối hoặc bằng `API_BASE_URL` lúc build.

API công khai: [kiểm tra trạng thái](https://tranvanvu-2380602601-api.onrender.com/health), [tài liệu API](https://tranvanvu-2380602601-api.onrender.com/docs). Email OTP và các luồng nghiệp vụ vẫn cần nghiệm thu thật theo [trạng thái kiểm chứng](docs/KIEM_CHUNG.md).

## Đối chiếu đề

| Yêu cầu | Triển khai |
|---|---|
| Đăng ký qua email | Tên đăng nhập, họ tên, email, mật khẩu, xác nhận Email OTP |
| Đăng nhập + OTP | Đúng mật khẩu mới gửi Email OTP; OTP dùng một lần, hết hạn 10 phút, tối đa 5 lần nhập sai |
| Phân quyền | Admin vào trang quản trị; nhân viên vào dashboard cá nhân; API kiểm tra quyền và chủ sở hữu |
| CRUD | Nhân viên; điểm chấm công; ca làm; phân ca; yêu cầu điều chỉnh đang chờ duyệt |
| b — chia sẻ vị trí | GPS thật, độ chính xác, khoảng cách đến điểm chấm công, mở bản đồ, chia sẻ qua Android |
| d — đo chuyển động | Cảm biến gia tốc không bao gồm trọng lực, lấy mẫu 3 giây, đồ thị và RMS m/s² |
| e — QR | Admin hiển thị QR ký trên máy chủ, nhân viên quét camera; hạn 90 giây, tự làm mới |
| Tính năng tự đề xuất | Hồ sơ giải trình công gồm GPS/sai số, QR, mẫu chuyển động và các nguyên nhân bị từ chối; duyệt có nhật ký trước/sau |
| Giao diện | Giao diện tiếng Việt riêng cho bài của Vũ, tông xanh, bố cục thích ứng, trạng thái tải/lỗi/rỗng |
| API deploy | Có `render.yaml`, Dockerfile, hướng dẫn Render + PostgreSQL; cần cấu hình tài khoản dịch vụ |

Đăng ký email là phương án được chọn trong hai phương án của đề. Không triển khai đăng ký qua bên thứ ba; OAuth 2.0 cho bên thứ ba không thuộc phương án đang chọn.

## Tên project

- Thư mục nộp, tên project Gradle, nhãn Android và tên APK: **TranVanVu_2380602601**.
- Dart bắt buộc tên package chữ thường: `tranvanvu_2380602601` trong `pubspec.yaml`.
- Android application ID: `vn.edu.tranvanvu.tranvanvu_2380602601`.

Đây là frontend cá nhân của Vũ. Thành viên có thể cài để kiểm thử, dùng chung backend; mỗi người phải tự có frontend khác khi nộp theo quy định giảng viên.

## Chạy Flutter

Môi trường đã dùng: Flutter **3.47.4**, Dart **3.13.3**, JDK **21**, Android SDK **36**; APK thực tế yêu cầu Android tối thiểu **7.0 / API 24**. Dùng cùng phiên bản Flutter để tránh lệch dependency. Giữ `pubspec.lock`.

```powershell
cd D:\KiemTraLTDD\TranVanVu_2380602601
flutter pub get
flutter devices
flutter run -d MA_THIET_BI_ANDROID
```

Mở app để đăng nhập vào API Render mặc định. Nếu dùng backend khác, chọn **Thiết lập kết nối** và nhập URL HTTPS đã deploy; cấu hình được lưu trên từng thiết bị.

Hoặc nhúng URL thật từ lúc chạy/build:

```powershell
flutter run -d MA_THIET_BI_ANDROID --dart-define=API_BASE_URL=https://TEN_API_THAT.onrender.com
.\scripts\build_android.ps1 -ApiBaseUrl https://TEN_API_THAT.onrender.com
```

Có thể build bằng `.\scripts\build_android.ps1` để dùng URL mặc định. APK ở `artifacts/TranVanVu_2380602601.apk`.

## Cấu trúc

```text
lib/src/              Flutter: tài khoản, dashboard, CRUD, chấm công, cảm biến, giải trình
backend/app/          FastAPI: xác thực, quyền, nghiệp vụ, mail, database
backend/tests/        Kiểm thử API và nghiệp vụ
test/                 Kiểm thử Flutter và bố cục màn hình hẹp
deploy/email/         Cầu nối Google Apps Script gửi OTP qua HTTPS
render.yaml           Deploy backend và PostgreSQL
docs/                 Deploy, demo, tính năng mới và trạng thái kiểm chứng
scripts/              Kiểm tra và build Android
```

## Kiểm tra source

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
cd ..
flutter analyze
flutter test
node deploy/email/test_bridge.cjs
```

Kiểm tra cảm biến và secure storage trên điện thoại thật (bản test sẽ mở trang đo chuyển động):

```powershell
flutter test integration_test/device_smoke_test.dart -d MA_THIET_BI_ANDROID
```

Sau đó cài lại APK release để trở về ứng dụng chính.

Để kiểm tra đăng nhập OTP thật và CRUD trên API đã deploy, chạy trực tiếp trong terminal cá nhân:

```powershell
python scripts/verify_live_backend.py
```

Script đọc cấu hình riêng `backend/.env.deploy`, yêu cầu nhập OTP trong terminal ở chế độ ẩn, tạo dữ liệu có tên kiểm tra tạm rồi dọn đúng các bản ghi vừa tạo. Kết quả ở `artifacts/live_api_report.json`; nhật ký thao tác phía máy chủ vẫn được giữ. Chưa chạy live script này thì không coi luồng OTP và CRUD production là đã nghiệm thu.

Backend test dùng database SQLite tạm và mail giả lập **chỉ trong test**, không gửi email. Khi production, backend bắt buộc PostgreSQL. Flutter test sử dụng dữ liệu fixture trong thư mục `test/`; chúng không được đóng gói vào app.

## Quy tắc nghiệp vụ

- Nhân viên chỉ được xem ca, công và yêu cầu của mình; không tự chọn vai trò admin khi đăng ký.
- Chấm công trong khoảng từ 2 giờ trước ca đến 4 giờ sau ca. Ca qua đêm được tính theo ngày bắt đầu ca (giờ Việt Nam).
- GPS phải ở trong bán kính được khai báo, sai số không quá 100 m, mẫu mới trong 90 giây; từ chối cờ vị trí mô phỏng do Android cung cấp.
- QR đúng điểm, còn hạn, đúng phiên bản. Thay đổi điểm chấm công làm QR cũ mất hiệu lực.
- Khi gửi chấm công, lấy lại vị trí và mẫu chuyển động; thời gian ghi công lấy từ máy chủ.
- Không cho vào trùng, ra trước vào, ra trùng; phân ca trùng giờ bị từ chối.
- Đi muộn nếu giờ vào quá thời gian bắt đầu + số phút cho phép.
- Dữ liệu đã có lịch sử được bảo vệ bằng khóa ngoại; khóa nhân viên hoặc tạo ca mới thay vì xóa lịch sử.
- Chỉ admin duyệt yêu cầu; admin không tự duyệt yêu cầu của mình. Việc điều chỉnh lưu dữ liệu trước đó và người duyệt trong nhật ký.
- Chuyển động là dữ liệu hỗ trợ giải trình, không chứng minh danh tính hoặc chống giả mạo cảm biến tuyệt đối.

Tài liệu nghiệp vụ của sản phẩm tham khảo và giới hạn về tuyên bố tính mới nằm ở [TINH_NANG_MOI.md](docs/TINH_NANG_MOI.md).
