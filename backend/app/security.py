import hashlib
import hmac
import secrets
from datetime import timedelta
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import config, mailer
from .db import (User, Challenge, AuthSession, BiometricDevice,
    BiometricSessionLink, Throttle, get_db, now, aware)

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash(secrets.token_urlsafe(24))
bearer = HTTPBearer(auto_error=False)

def code_hash(challenge_id, code):
    return hmac.new(config.SECRET_KEY.encode(), f'{challenge_id}:{code}'.encode(), hashlib.sha256).hexdigest()

def throttle(db, key, limit=10, seconds=900):
    digest = hashlib.sha256(key.encode()).hexdigest()
    row = db.scalar(select(Throttle).where(Throttle.id == digest).with_for_update())
    if row is None:
        row = Throttle(id=digest, attempts=0, window_start=now())
        db.add(row)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            row = db.scalar(select(Throttle).where(Throttle.id == digest).with_for_update())
    if (now() - aware(row.window_start)).total_seconds() > seconds:
        row.window_start, row.attempts = now(), 0
    if row.attempts >= limit:
        raise HTTPException(429, 'Bạn đã thử quá nhiều lần. Vui lòng đợi 15 phút.')
    row.attempts += 1
    db.commit()

def issue_challenge(db, user, purpose):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    # One active challenge per user. Never return or log the OTP.
    previous = db.scalar(select(Challenge).where(Challenge.user_id == user.id,
        Challenge.used == False).order_by(Challenge.issued_at.desc()))
    if previous and (now() - aware(previous.issued_at)).total_seconds() < 60:
        raise HTTPException(429, 'Đã gửi email. Vui lòng đợi 60 giây trước khi yêu cầu mã mới.')
    row = Challenge(user_id=user.id, purpose=purpose, code_hash='', expires_at=now() + timedelta(seconds=config.OTP_SECONDS))
    db.add(row)
    db.flush()
    code = f'{secrets.randbelow(1000000):06d}'
    row.code_hash = code_hash(row.id, code)
    try:
        mailer.send_otp(user.email, code)
    except Exception:
        db.rollback()
        raise HTTPException(503, 'Chưa gửi được OTP. Kiểm tra cấu hình email máy chủ hoặc thử lại sau.')
    if previous: previous.used = True
    db.commit()
    return challenge_response(row, user)

def challenge_response(row, user):
    local, domain = user.email.split('@')
    return {'challenge_id': row.id, 'email_hint': f'{local[:2]}***@{domain}',
            'expires_in': config.OTP_SECONDS, 'resend_after': 60}

def signed(payload, seconds, kind):
    return jwt.encode({**payload, 'typ': kind, 'iat': now(),
        'exp': now() + timedelta(seconds=seconds), 'iss': 'tranvanvu-attendance'}, config.SECRET_KEY, algorithm='HS256')

def decode(token, kind):
    try:
        data = jwt.decode(token, config.SECRET_KEY, algorithms=['HS256'],
            issuer='tranvanvu-attendance', options={'require': ['exp', 'iat', 'iss', 'typ']})
        if data['typ'] != kind: raise ValueError('Token type')
        return data
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, 'Mã hoặc phiên đã hết hạn, vui lòng thử lại.')

def create_session(db, user, method='password_otp', device_id=None):
    if method not in ('password_otp', 'face', 'fingerprint'):
        raise ValueError('Unsupported authentication method.')
    if method != 'password_otp':
        device = db.scalar(select(BiometricDevice).where(BiometricDevice.id == device_id)
                           .with_for_update().execution_options(populate_existing=True))
        if (device is None or device.user_id != user.id or device.kind != method
                or device.revoked or aware(device.expires_at) <= now()):
            raise HTTPException(401, 'Thiết bị đăng nhập không còn hợp lệ.')
        # Revocation/deactivation may have happened while camera inference ran.
        db.refresh(user)
        if not user.active or not user.verified:
            raise HTTPException(401, 'Tài khoản chưa xác thực hoặc đã bị khóa.')
    row = AuthSession(user_id=user.id, expires_at=now() + timedelta(hours=config.TOKEN_HOURS))
    db.add(row)
    db.flush()
    claims = {'sub': user.id, 'jti': row.id, 'auth_method': method,
              'auth_time': int(now().timestamp())}
    if method != 'password_otp':
        claims['device_id'] = device_id
        db.add(BiometricSessionLink(session_id=row.id, device_id=device_id))
    token = signed(claims, config.TOKEN_HOURS * 3600, 'access')
    db.commit()
    return token

def current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if credentials is None: raise HTTPException(401, 'Vui lòng đăng nhập.')
    data = decode(credentials.credentials, 'access')
    session = db.get(AuthSession, data.get('jti'))
    user = db.get(User, data.get('sub'))
    if not session or session.revoked or session.user_id != data.get('sub') or aware(session.expires_at) <= now():
        raise HTTPException(401, 'Phiên đăng nhập đã hết hạn.')
    if not user or not user.active or not user.verified:
        raise HTTPException(401, 'Tài khoản chưa xác thực hoặc đã bị khóa.')
    if data.get('auth_method') in ('face', 'fingerprint'):
        device = db.get(BiometricDevice, data.get('device_id'))
        link = db.get(BiometricSessionLink, session.id)
        if (device is None or link is None or link.device_id != device.id
                or device.user_id != user.id or device.kind != data['auth_method']
                or device.revoked or aware(device.expires_at) <= now()):
            raise HTTPException(401, 'Đăng nhập sinh trắc học đã bị thu hồi hoặc hết hạn.')
    request.state.auth_session_id = session.id
    request.state.auth_claims = data
    return user

def admin(user: User = Depends(current_user)):
    if user.role != 'admin': raise HTTPException(403, 'Chỉ quản trị viên được thực hiện chức năng này.')
    return user
