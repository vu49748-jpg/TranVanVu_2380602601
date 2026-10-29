# TranVanVu_2380602601

Ứng dụng **chấm công nhân viên** — Trần Văn Vũ, MSSV **2380602601**, **nhóm 7**.

Ứng dụng di động viết bằng **Flutter**, dành cho **Android**. Backend **FastAPI + PostgreSQL**. Chọn ba mục **b: chia sẻ vị trí**, **d: đo chuyển động**, **e: quét QR**.

## Trạng thái trước khi nộp

API HTTPS đã deploy trên Render và kết nối PostgreSQL thành công. Đã xác nhận **đăng nhập admin bằng mật khẩu + Email OTP thật** trên ASUS Android 13 và emulator Pixel_7, vào đúng Trang quản trị. Tài khoản `nhanvienvu` đã đăng ký và xác minh email thật; trên ASUS đã vào đúng dashboard **NHÂN VIÊN**, có nút chấm công của mình và không có menu quản trị. Người dùng xác nhận **chấm công vào thành công bằng GPS thật và camera ASUS quét QR hiển thị trên Pixel_7**, sau đó đã chấm công ra. Lịch sử thật trên ASUS ghi ca `CA DEMO VU` ngày 29/10/2026 vào 18:21, ra 18:28 (GMT+7), hiển thị 0.1 giờ công hoàn tất.

Đã kiểm thử đầy đủ **thêm, xem, sửa, xóa nhân viên, điểm chấm công, ca làm và phân ca qua giao diện Flutter thật trên ASUS**. Các bản ghi tạm của đợt CRUD đã được dọn và admin ban đầu được giữ nguyên; sau đó đã tạo, giữ lại điểm `DEMO VU`, ca `CA DEMO VU` và phân ca để demo chấm công. Cảm biến gia tốc và secure storage đã qua integration test trên ASUS; bản release cũng hiển thị 49 mẫu thật, RMS 0.00 m/s² khi điện thoại đứng yên. Bộ widget test hiện **6/6 qua**, gồm hồi quy nhập `23:59` khi hệ thống dùng giờ 12 tiếng. APK mới đã được cài trên ASUS/Pixel_7, giữ phiên đăng nhập; trên Pixel_7 đã nhập và xác nhận `23:58` thành công, hộp thoại đóng và form hiện đúng giờ. Thử nghiệm này không lưu form, nên ca demo vẫn giữ 08:00–23:59.

Trên ASUS đã lấy GPS thật và mở **bảng chia sẻ Android** với liên kết Google Maps chứa vị trí thật trong bản xem trước; đã đóng bảng chia sẻ mà không chọn người nhận, nên chưa gửi hay xác nhận giao liên kết cho bên ngoài.

Luồng **giải trình có bằng chứng và phê duyệt trên production đã được kiểm thử thật** bằng ca riêng `CA KIEM THU GIAI TRINH` 06:00–07:00. Chấm công ngoài khung giờ bị từ chối đúng; nhân viên gửi rồi sửa yêu cầu kèm GPS/QR/chuyển động, admin xem hồ sơ và duyệt với nhận xét ghi rõ KIỂM THỬ. Nhật ký có dữ liệu trước điều chỉnh và mã yêu cầu; ASUS tải lại thấy ca thử 06:00–07:00 ở trạng thái Đã điều chỉnh, còn bản ghi thật 18:21–18:28 giữ nguyên. Đây là giờ đề xuất của ca kiểm thử được admin duyệt, không phải giờ chấm công thực tế buổi sáng.

Các luồng chính đã chạy qua API công khai và thiết bị thật. Phần xác minh bổ sung còn lại: **từ chối chấm công riêng vì QR hết hạn trên một ca còn mở và đúng khung giờ**, độ bền dữ liệu qua restart backend và việc chạy trên máy tất cả thành viên. QR hết hạn đã được phát hiện trong hồ sơ giải trình lúc lưu và có test backend offline, nhưng chưa thay thế kiểm thử âm riêng của endpoint chấm công. Người dùng hiện chưa có thêm Android của thành viên khác để thử, nên mục cả nhóm chạy vẫn chờ xác nhận sau. Xem [trạng thái kiểm chứng](docs/KIEM_CHUNG.md) và [kịch bản nghiệm thu](docs/DEMO.md).

APK release cuối có bản sửa nhập giờ 24 tiếng và nhãn bằng chứng chính xác **“GPS và QR đạt kiểm tra”**; nhãn này chỉ mô tả các điều kiện GPS/QR, không xác nhận toàn bộ điều kiện chấm công. Kết quả kiểm tra: **6 widget test**, **26 backend test offline**, **1 integration test bằng cảm biến/secure storage thật** và analyzer không có vấn đề.

Ứng dụng **không nhúng thông tin đăng nhập hoặc OTP giả**, không trả OTP về app và không dùng endpoint localhost. Tài khoản demo là tài khoản thật dùng mật khẩu và Email OTP; thông tin đăng nhập demo được lưu riêng trong file `.env` đã loại khỏi Git, không đóng gói vào APK/source nộp bài. App mặc định kết nối API đã deploy tại `https://tranvanvu-2380602601-api.onrender.com`; có thể thay máy chủ trong phần thiết lập kết nối hoặc bằng `API_BASE_URL` lúc build.

API công khai: [kiểm tra trạng thái](https://tranvanvu-2380602601-api.onrender.com/health), [tài liệu API](https://tranvanvu-2380602601-api.onrender.com/docs). `/health` đã trả HTTP 200, đúng project và thực hiện truy vấn PostgreSQL thành công; việc nhận OTP admin thật và CRUD production được xác nhận riêng qua ứng dụng Android.

## Đối chiếu đề

| Yêu cầu | Triển khai |
|---|---|
| Đăng ký qua email | Người dùng đã xác nhận đăng ký và xác minh email thật của tài khoản `nhanvienvu` trên API công khai |
| Đăng nhập + OTP | Đã xác nhận admin dùng mật khẩu + OTP email thật trên ASUS/Pixel_7 và nhân viên đã xác minh vào app trên ASUS; mã dùng một lần, hết hạn 10 phút, tối đa 5 lần nhập sai |
| Phân quyền | Admin vào Trang quản trị; ASUS đã hiển thị đúng dashboard NHÂN VIÊN, nút chấm công cá nhân và không có menu quản trị cho `nhanvienvu`; API có kiểm tra quyền và chủ sở hữu |
| CRUD | Nhân viên, điểm chấm công, ca làm và phân ca đã qua đầy đủ CRUD bằng giao diện ASUS với API Render, dọn sạch dữ liệu tạm; tạo/xem/sửa giải trình kèm bằng chứng và admin phê duyệt cũng đã kiểm thử live |
| b — chia sẻ vị trí | GPS thật đã dùng để vào ca; đã mở bảng chia sẻ Android với liên kết Google Maps có vị trí thật trong bản xem trước, rồi đóng mà không chọn người nhận |
| d — đo chuyển động | Đã lấy mẫu gia tốc thật trên ASUS qua integration test 3 giây; bản release hiển thị 49 mẫu, RMS 0.00 m/s² khi máy đứng yên; có đồ thị và kết quả đo |
| e — QR | Đã quét QR từ Pixel_7 bằng camera ASUS và chấm công vào thành công qua API Render; QR ký trên máy chủ, hạn 90 giây và tự làm mới |
| Tính năng tự đề xuất | Hồ sơ giải trình công có GPS/sai số, QR, mẫu chuyển động; đã thử lưu/sửa hồ sơ, xem cờ QR hết hạn và phê duyệt có nhật ký điều chỉnh. Đây là đề xuất của bài, không khẳng định độc nhất trên thị trường |
| Giao diện | Giao diện tiếng Việt riêng cho bài của Vũ, tông xanh, bố cục thích ứng, trạng thái tải/lỗi/rỗng; bản sửa giờ 24 tiếng đã xác nhận nhập 23:58 thành công trên Pixel_7 dùng hệ thống 12 giờ |
| API deploy | Đã deploy tại `https://tranvanvu-2380602601-api.onrender.com`, kết nối PostgreSQL và xác nhận `/health` thành công; có `render.yaml`, Dockerfile và hướng dẫn tái triển khai |

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

Có thể dùng công cụ tùy chọn sau để kiểm tra lại đăng nhập OTP thật và CRUD trên API đã deploy từ terminal cá nhân:

```powershell
python scripts/verify_live_backend.py
```

Script đọc cấu hình riêng `backend/.env.deploy`, yêu cầu nhập OTP trong terminal ở chế độ ẩn, tạo dữ liệu có tên kiểm tra tạm rồi dọn đúng các bản ghi vừa tạo. Kết quả ở `artifacts/live_api_report.json`; nhật ký thao tác phía máy chủ vẫn được giữ. Đây là cách tái lập kiểm tra tùy chọn: đăng nhập admin bằng OTP thật và CRUD production đã được kiểm chứng qua giao diện Android thực tế. Công cụ CLI chưa được chạy trên production; các kiểm thử của chính công cụ dùng API giả lập offline.

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
