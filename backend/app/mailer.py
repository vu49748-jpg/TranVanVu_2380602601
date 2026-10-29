import os
import time
import secrets
import hmac
import hashlib
import smtplib
from email.message import EmailMessage
import httpx
from .config import EMAIL_TRANSPORT, APP_ENV

def send_otp(email: str, code: str):
    subject = 'Mã xác thực Chấm công • Trần Văn Vũ'
    content = f'Mã xác thực của bạn: {code}\nCó hiệu lực trong 10 phút. Không chia sẻ mã với người khác.'
    if EMAIL_TRANSPORT == 'apps_script':
        url, secret = os.getenv('GAS_WEBHOOK_URL', ''), os.getenv('GAS_SHARED_SECRET', '')
        if not url.startswith('https://script.google.com/macros/s/') or not url.endswith('/exec') or len(secret) < 32:
            raise RuntimeError('Chưa cấu hình Google Apps Script gửi OTP.')
        timestamp, nonce = str(int(time.time())), secrets.token_hex(16)
        canonical = '|'.join([email, code, timestamp, nonce])
        signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        response = httpx.post(url, json={'email':email, 'code':code, 'timestamp':timestamp,
            'nonce':nonce, 'signature':signature}, timeout=25, follow_redirects=True)
        response.raise_for_status()
        if response.json().get('ok') is not True:
            raise RuntimeError('Apps Script từ chối gửi OTP. Kiểm tra cấu hình/quota.')
    elif EMAIL_TRANSPORT == 'resend':
        key, sender = os.getenv('RESEND_API_KEY'), os.getenv('MAIL_FROM')
        if not key or not sender: raise RuntimeError('Chưa cấu hình email Resend.')
        response = httpx.post('https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {key}'},
            json={'from': sender, 'to': [email], 'subject': subject, 'text': content}, timeout=20)
        response.raise_for_status()
    elif EMAIL_TRANSPORT == 'smtp':
        host, sender = os.getenv('SMTP_HOST'), os.getenv('MAIL_FROM')
        if not host or not sender: raise RuntimeError('Chưa cấu hình SMTP gửi email.')
        message = EmailMessage()
        message['From'], message['To'], message['Subject'] = sender, email, subject
        message.set_content(content)
        port = int(os.getenv('SMTP_PORT', '587'))
        client_cls = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
        with client_cls(host, port, timeout=20) as client:
            if port != 465: client.starttls()
            client.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
            client.send_message(message)
    else:
        raise RuntimeError('Cần dịch vụ gửi email thật. Không hỗ trợ OTP giả trong ứng dụng.')
