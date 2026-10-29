# Đưa API lên Internet và bật Email OTP thật

Backend phải được deploy để nộp bài. Không dùng địa chỉ localhost, IP mạng nội bộ hay tunnel máy cá nhân cho bản demo cuối. Cần tài khoản **GitHub**, **Render**, **Gmail**. Các bước đăng nhập/cấp quyền do chủ tài khoản thực hiện.

## 1. Bật cầu nối gửi email bằng Gmail

Backend gọi Google Apps Script qua HTTPS; Apps Script dùng `MailApp` để gửi email. Hạn mức gửi phụ thuộc tài khoản Google. Theo [tài liệu quota](https://developers.google.com/apps-script/guides/services/quotas), tài khoản cá nhân có giới hạn người nhận mỗi ngày; kiểm tra quota hiện hành và không gửi lặp để thử quá nhiều lần.

1. Mở [Google Apps Script](https://script.google.com/) bằng Gmail cá nhân.
2. Tạo **New project**, đặt tên `TranVanVu_2380602601_EmailOTP`.
3. Mở file `Code.gs`, thay nội dung bằng [deploy/email/Code.gs](../deploy/email/Code.gs), lưu.
4. Tạo khóa ngẫu nhiên trên máy:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Giữ giá trị này riêng để dùng cho bước 5 và Render; không đưa vào Git, APK hoặc tin nhắn.

5. Trong **Project Settings → Script properties → Add script property**:
   - Property: `OTP_SHARED_SECRET`
   - Value: chuỗi ngẫu nhiên vừa tạo.
6. Chọn **Deploy → New deployment → Web app**.
   - Execute as: **Me**.
   - Who has access: **Anyone**.
   - Cấp quyền gửi email cho đúng project tự tạo. Mã nguồn chỉ dùng `MailApp` để gửi OTP; không đọc hộp thư.
7. Sao chép **Web app URL** dạng `https://script.google.com/macros/s/…/exec`. Dùng URL `/exec`, không dùng URL `/dev`.
8. Mở URL đó trong trình duyệt. Kết quả có `status: ready`. Đây mới là kiểm tra web app, chưa phải bằng chứng email đã gửi thành công.

Mặc dù URL công khai, `doPost` bắt buộc chữ ký HMAC SHA-256, hạn thời gian và nonce chống phát lại. Khóa chỉ ở Script Properties và backend. Sau khi sửa script, cần **Manage deployments → Edit → New version → Deploy**.

Tài liệu: [Apps Script Web Apps](https://developers.google.com/apps-script/guides/web), [MailApp](https://developers.google.com/apps-script/reference/mail/mail-app).

## 2. Đưa source lên GitHub

Dùng repository **private** tên `TranVanVu_2380602601`. Repository chứa thư mục `backend/` và file `render.yaml` ở gốc. Không upload `.env`, `.venv`, database test, keystore hoặc thư mục build.

Nếu repository đã được tạo/push trong phiên làm việc, dùng repository đó. Không tạo thêm bản khác hoặc công khai source.

## 3. Tạo Render Blueprint

1. Mở [Render Dashboard](https://dashboard.render.com/), đăng nhập bằng GitHub.
2. Chọn **New → Blueprint**, kết nối đúng repository private `TranVanVu_2380602601`.
3. Render đọc file `render.yaml`; kiểm tra web service và PostgreSQL đều chọn **Free** trước khi tạo.
4. Điền các biến Render hỏi:

   | Biến | Giá trị |
   |---|---|
   | `GAS_WEBHOOK_URL` | Web app URL `/exec` từ bước 1 |
   | `GAS_SHARED_SECRET` | Cùng giá trị với `OTP_SHARED_SECRET` |
   | `ADMIN_EMAIL` | Gmail thật dùng nhận OTP của admin |
   | `ADMIN_PASSWORD` | Mật khẩu admin mới, ít nhất 8 ký tự |

   `ADMIN_USERNAME` mặc định `tranvanvu`; `SECRET_KEY` được Render tự sinh; `DATABASE_URL` được nối với PostgreSQL.

5. Chọn tạo/deploy, đợi build và service chuyển **Live**.
6. Sao chép URL backend dạng `https://…onrender.com`.
7. Mở `/health`. Cần thấy `project: TranVanVu_2380602601`, `status: ok`, `email_configured: true`.
8. Mở `/docs` để xem tài liệu API tự động.
9. Sau lần khởi động đầu thành công, **xóa biến `ADMIN_PASSWORD` khỏi Environment** rồi redeploy. Admin đã lưu hash mật khẩu trong PostgreSQL. Không xóa `SECRET_KEY`, `DATABASE_URL` hay các biến gửi email.

Render free có thời gian ngủ khi không truy cập; lần gọi đầu có thể chậm. PostgreSQL free có thời hạn, cần xem ngày hết hạn và xuất dữ liệu trước khi dịch vụ hết hạn. File trên filesystem của web service free không phải nơi lưu dữ liệu bền vững, vì vậy project dùng PostgreSQL. [Tài liệu Render free](https://render.com/docs/free)

Không dùng SMTP Gmail trên Render free vì các cổng SMTP phổ biến bị chặn. Backend đã có Apps Script HTTPS; nếu có domain gửi mail xác thực có thể dùng Resend qua HTTPS. [Render: outbound port restrictions](https://render.com/docs/free#outbound-port-restrictions)

## 4. Kết nối app và thử OTP thật

1. Cài APK, mở app và nhập URL backend HTTPS.
2. Đăng nhập `tranvanvu` với mật khẩu đã đặt trên Render.
3. Mở Gmail để lấy OTP, nhập 6 số trong app. Lần đầu cũng xác thực quyền sở hữu email admin.
4. Kiểm tra vào đúng **Trang quản trị**, không vào dashboard nhân viên.
5. Đăng ký nhân viên bằng email khác. Có thể dùng bí danh Gmail dạng `ten+nhanvien@gmail.com` nếu hộp thư của bạn nhận được bí danh đó; ứng dụng vẫn gửi email thật.
6. Xác thực email đăng ký rồi đăng nhập bằng mật khẩu và một OTP mới.
7. Kiểm tra nhân viên chỉ thấy dashboard cá nhân.

OTP không được in vào log hoặc trả về API. Nếu không có email, kiểm tra Spam, Apps Script Executions, URL `/exec`, hai khóa giống nhau, quyền gửi và quota. Không đổi sang mã cố định để demo.

## 5. Chạy trên các máy khác

Mỗi máy cần Flutter/Android SDK, chạy `flutter pub get`, kết nối thiết bị rồi `flutter run`. Mỗi điện thoại dùng cùng URL backend đã deploy và tài khoản riêng để kiểm thử. Để nộp, từng người vẫn cần frontend cá nhân khác nhau theo đề.

## Lỗi thường gặp

- `503 Chưa gửi được OTP`: web app chưa deploy public, khóa sai, chưa cấp quyền hoặc hết quota email.
- `401`: mật khẩu sai/tài khoản khóa, hoặc phiên đăng nhập hết hạn; đăng nhập lại.
- `429`: đã yêu cầu OTP quá nhanh hoặc nhập mật khẩu quá nhiều; đợi theo thông báo.
- `409`: trùng dữ liệu, phân ca trùng hoặc đang xóa dữ liệu có lịch sử; đọc thông báo API.
- GPS lệch: bật định vị chính xác, ra nơi thoáng, lấy lại vị trí. Android có quyền vị trí gần đúng sẽ có thể không đủ chính xác.
- Không quét được QR: cấp quyền Camera và dùng mã còn hạn. Nhân viên quét QR của admin, không quét mã bất kỳ.
- Thiết bị báo vị trí mô phỏng: chấm công bằng điện thoại thật; app chủ động từ chối mẫu Android đánh dấu giả lập.
