"""Optional device-bound login after an explicit, recent password + OTP login.

Fingerprint proof is signed by the Android auth-per-use key. Camera-face proof
uses a separate device key plus server-side face matching and a randomized pose
sequence. The server does not claim hardware attestation or certified 3-D PAD.
"""
import base64
import binascii
import hashlib
import json
import secrets
from datetime import timedelta

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config, schemas, security
from .db import (Audit, AuthSession, BiometricChallenge, BiometricDevice,
                 BiometricSessionLink, User, aware, get_db, now, public, uid)

router = APIRouter()
CHALLENGE_SECONDS = 120
ENROLLMENT_SECONDS = 600
DEVICE_DAYS = 30
MAX_REQUEST_BYTES = 4_500_000
MAX_IMAGE_BYTES = 786_432
LOGIN_FAILURE = 'Không xác thực được sinh trắc học. Hãy thử lại hoặc dùng mật khẩu và OTP.'


class BiometricBodyLimitMiddleware:
    """Bound JSON before FastAPI parses base64 images, including chunked bodies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope.get('path', '').startswith('/auth/biometric/'):
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            if message['type'] != 'http.request':
                continue
            total += len(message.get('body', b''))
            if total > MAX_REQUEST_BYTES:
                return await JSONResponse(
                    status_code=413,
                    content={'detail': 'Ảnh vượt giới hạn. Vui lòng chụp lại với kích thước nhỏ hơn.'},
                )(scope, receive, send)
            chunks.append(message)
            if not message.get('more_body', False):
                break
        iterator = iter(chunks)

        async def bounded_receive():
            return next(iterator, {'type': 'http.request', 'body': b'', 'more_body': False})

        return await self.app(scope, bounded_receive, send)


def _face_api():
    # Importing normal attendance/OTP routes never loads OpenCV or face weights.
    from . import face_engine
    return face_engine


def face_ready():
    try:
        return bool(_face_api().face_ready())
    except (ImportError, OSError, RuntimeError):
        return False


def _fresh_claims(request):
    claims = getattr(request.state, 'auth_claims', {})
    auth_time = claims.get('auth_time')
    return (claims.get('auth_method') == 'password_otp'
            and isinstance(auth_time, (int, float)) and not isinstance(auth_time, bool)
            and 0 <= now().timestamp() - auth_time <= ENROLLMENT_SECONDS)


def _require_fresh_otp(request):
    if not _fresh_claims(request):
        raise HTTPException(403, {
            'message': 'Để bật sinh trắc học, hãy xác thực lại bằng mật khẩu và Email OTP trong 10 phút gần nhất.',
            'code': 'fresh_otp_required',
        })


def _audit(db, user_id, action, entity_id, details=None):
    # Never put photos, templates, public keys, signatures or nonces in audit logs.
    db.add(Audit(user_id=user_id, action=action, entity_id=entity_id, details=details or {}))


def _device_view(row):
    return {
        'id': row.id, 'kind': row.kind, 'device_name': row.device_name,
        'created_at': aware(row.created_at).isoformat(),
        'expires_at': aware(row.expires_at).isoformat(),
        'last_used_at': aware(row.last_used_at).isoformat() if row.last_used_at else None,
        'revoked': row.revoked,
        'active': not row.revoked and aware(row.expires_at) > now(),
    }


def _decode_public_key(value):
    try:
        raw = base64.b64decode(value, validate=True)
        key = serialization.load_der_public_key(raw)
        if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
            raise ValueError('Unsupported curve')
        canonical = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if canonical != raw:
            raise ValueError('Noncanonical key')
        return key, base64.b64encode(canonical).decode('ascii'), hashlib.sha256(canonical).hexdigest()
    except (ValueError, TypeError, binascii.Error):
        raise HTTPException(400, 'Khóa thiết bị không hợp lệ. Vui lòng thiết lập lại sinh trắc học.')


def _decode_images(values):
    result = []
    for value in values:
        try:
            image = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(400, 'Ảnh khuôn mặt không hợp lệ. Vui lòng chụp lại.')
        if not 128 <= len(image) <= MAX_IMAGE_BYTES or not image.startswith(b'\xff\xd8'):
            raise HTTPException(400, 'Cần ảnh JPEG từ camera, mỗi ảnh không quá 768 KB.')
        result.append(image)
    return result


def signature_message(challenge, images):
    """Shared wire contract: challenge, then newline-separated JPEG SHA256s."""
    if not images:
        return challenge.encode('utf-8')
    return (challenge + '\n' + '\n'.join(hashlib.sha256(image).hexdigest() for image in images)).encode('utf-8')


def _verify_signature(public_key, signature, challenge, images):
    key, _, _ = _decode_public_key(public_key)
    try:
        raw_signature = base64.b64decode(signature, validate=True)
        if not 64 <= len(raw_signature) <= 80:
            return False
        key.verify(raw_signature, signature_message(challenge, images), ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, TypeError, binascii.Error):
        return False


def _template_cipher():
    key = HKDF(algorithm=hashes.SHA256(), length=32,
               salt=b'TranVanVu_2380602601/face-template/v1',
               info=b'authenticated-face-reference-encryption').derive(config.SECRET_KEY.encode('utf-8'))
    return AESGCM(key)


def _template_aad(user_id, device_id):
    return f'TranVanVu_2380602601|face-reference|v1|{user_id}|{device_id}'.encode('utf-8')


def _encrypt_template(templates, user_id, device_id):
    nonce = secrets.token_bytes(12)
    data = json.dumps(templates, allow_nan=False, separators=(',', ':')).encode('utf-8')
    ciphertext = _template_cipher().encrypt(nonce, data, _template_aad(user_id, device_id))
    return base64.b64encode(nonce + ciphertext).decode('ascii')


def _decrypt_template(value, user_id, device_id):
    try:
        raw = base64.b64decode(value, validate=True)
        data = _template_cipher().decrypt(raw[:12], raw[12:], _template_aad(user_id, device_id))
        return json.loads(data)
    except (InvalidTag, ValueError, TypeError, binascii.Error, UnicodeError):
        raise HTTPException(401, LOGIN_FAILURE)


def _steps(kind):
    if kind != 'face':
        return []
    turns = ['turn_left', 'turn_right']
    if secrets.randbelow(2):
        turns.reverse()
    return ['front', *turns, 'front']


def _new_challenge(db, user_id, device_id, kind, purpose, public_key=None, device_name=''):
    row = BiometricChallenge(
        id=uid(), user_id=user_id, device_id=device_id, kind=kind, purpose=purpose,
        pending_key=public_key, device_name=device_name, steps=_steps(kind),
        payload='', issued_at=now(), expires_at=now() + timedelta(seconds=CHALLENGE_SECONDS),
    )
    row.payload = f'TranVanVu_2380602601|biometric-v1|{purpose}|{kind}|{row.id}|{device_id}|{secrets.token_urlsafe(32)}'
    # Expired proof requests carry no photos. Keep short-lived metadata for one day.
    db.execute(delete(BiometricChallenge).where(BiometricChallenge.expires_at < now() - timedelta(days=1)))
    db.add(row)
    db.commit()
    return row


def _challenge_view(row):
    return {'challenge_id': row.id, 'device_id': row.device_id, 'kind': row.kind,
            'challenge': row.payload, 'expires_in': CHALLENGE_SECONDS, 'steps': row.steps}


def _consume(db, row):
    # A conditional UPDATE is atomic on PostgreSQL AND SQLite. Commit the burn
    # before signature/ML work so invalid proofs and concurrent replay both fail.
    result = db.execute(update(BiometricChallenge).where(
        BiometricChallenge.id == row.id, BiometricChallenge.used == False,
        BiometricChallenge.expires_at > now()).values(used=True),
        execution_options={'synchronize_session': False})
    db.commit()
    if result.rowcount != 1:
        raise HTTPException(400 if row.purpose == 'enroll' else 401,
                            'Yêu cầu sinh trắc học đã dùng hoặc hết hạn. Vui lòng thử lại.')


def _load_challenge(db, id, purpose):
    row = db.get(BiometricChallenge, id)
    if row is None or row.purpose != purpose or row.used or aware(row.expires_at) <= now():
        raise HTTPException(400 if purpose == 'enroll' else 401,
                            'Yêu cầu sinh trắc học đã dùng hoặc hết hạn. Vui lòng thử lại.')
    return row


def _load_device(db, id):
    row = db.get(BiometricDevice, id)
    if row is None or row.revoked or aware(row.expires_at) <= now():
        raise HTTPException(401, LOGIN_FAILURE)
    user = db.get(User, row.user_id)
    if user is None or not user.active or not user.verified:
        raise HTTPException(401, LOGIN_FAILURE)
    return row, user


def _face_call(function, *arguments, enrollment=False):
    try:
        api = _face_api()
        if not api.face_ready():
            raise FileNotFoundError('Face models unavailable')
        return getattr(api, function)(*arguments)
    except (ImportError, FileNotFoundError):
        raise HTTPException(503, 'Nhận diện khuôn mặt hiện chưa sẵn sàng. Hãy thử lại hoặc dùng mật khẩu và OTP.')
    except ValueError as error:
        # Only the engine's deliberately safe error text may be shown at setup.
        safe = getattr(error, 'message', 'Chưa lấy được khuôn mặt phù hợp. Hãy chụp lại.')
        raise HTTPException(400 if enrollment else 401, safe if enrollment else LOGIN_FAILURE)
    except RuntimeError:
        raise HTTPException(503, 'Nhận diện khuôn mặt đang bận. Vui lòng thử lại.')


@router.get('/me/security')
def security_status(request: Request, user=Depends(security.current_user), db: Session = Depends(get_db)):
    devices = db.scalars(select(BiometricDevice).where(BiometricDevice.user_id == user.id)
                         .order_by(BiometricDevice.created_at.desc())).all()
    return {'auth_method': request.state.auth_claims.get('auth_method', 'legacy'),
            'can_enroll_biometrics': _fresh_claims(request),
            'enrollment_window_seconds': ENROLLMENT_SECONDS,
            'face_ready': face_ready(), 'devices': [_device_view(row) for row in devices]}


@router.get('/me/biometric-devices')
def list_devices(user=Depends(security.current_user), db: Session = Depends(get_db)):
    return [_device_view(row) for row in db.scalars(select(BiometricDevice)
            .where(BiometricDevice.user_id == user.id).order_by(BiometricDevice.created_at.desc()))]


@router.post('/auth/biometric/enrollment-challenge', status_code=201)
def enrollment_challenge(data: schemas.BiometricEnrollment, request: Request,
                         user=Depends(security.current_user), db: Session = Depends(get_db)):
    _require_fresh_otp(request)
    security.throttle(db, f'biometric-enroll:{user.id}', limit=12)
    _, canonical, fingerprint = _decode_public_key(data.public_key)
    if data.kind == 'face' and not face_ready():
        raise HTTPException(503, 'Máy chủ chưa sẵn sàng nhận diện khuôn mặt. Hãy thử lại sau.')
    active = db.scalars(select(BiometricDevice.id).where(BiometricDevice.user_id == user.id,
        BiometricDevice.revoked == False, BiometricDevice.expires_at > now())).all()
    if len(active) >= 10:
        raise HTTPException(409, 'Bạn đã có 10 thiết lập sinh trắc học. Hãy thu hồi một thiết bị trước.')
    if db.scalar(select(BiometricDevice.id).where(BiometricDevice.key_fingerprint == fingerprint)):
        raise HTTPException(409, 'Khóa thiết bị này đã được đăng ký. Hãy tạo thiết lập mới.')
    return _challenge_view(_new_challenge(db, user.id, uid(), data.kind, 'enroll', canonical, data.device_name))


@router.post('/auth/biometric/enroll', status_code=201)
def enroll(data: schemas.BiometricProof, request: Request,
           user=Depends(security.current_user), db: Session = Depends(get_db)):
    _require_fresh_otp(request)
    row = _load_challenge(db, data.challenge_id, 'enroll')
    if row.user_id != user.id:
        raise HTTPException(403, 'Thiết lập sinh trắc học không thuộc tài khoản của bạn.')
    _consume(db, row)
    images = _decode_images(data.images)
    if not _verify_signature(row.pending_key, data.signature, row.payload, images):
        raise HTTPException(400, 'Không xác minh được khóa thiết bị. Hãy bắt đầu thiết lập lại.')
    if row.kind == 'fingerprint' and images:
        raise HTTPException(400, 'Thiết lập vân tay không nhận ảnh khuôn mặt.')
    template = None
    if row.kind == 'face':
        if len(images) != len(row.steps):
            raise HTTPException(400, 'Hãy hoàn tất đủ các bước chụp khuôn mặt.')
        if (now() - aware(row.issued_at)).total_seconds() < 2:
            raise HTTPException(400, 'Hãy thực hiện từng bước chuyển động khuôn mặt rồi thử lại.')
        templates = _face_call('enroll_faces', images, row.steps, enrollment=True)
        template = _encrypt_template(templates, user.id, row.device_id)
    _, canonical, fingerprint = _decode_public_key(row.pending_key)
    # Camera inference can take time. Re-read authoritative account/session
    # state after it finishes; SQLAlchemy's identity map must not retain the
    # active account or OTP session observed before a concurrent revocation.
    user = db.scalar(select(User).where(User.id == user.id).with_for_update()
                     .execution_options(populate_existing=True))
    if user is None or not user.active or not user.verified:
        raise HTTPException(401, 'Tài khoản chưa xác thực hoặc đã bị khóa.')
    auth_session = db.scalar(select(AuthSession).where(
        AuthSession.id == request.state.auth_session_id).with_for_update()
        .execution_options(populate_existing=True))
    if (auth_session is None or auth_session.revoked or auth_session.user_id != user.id
            or aware(auth_session.expires_at) <= now()):
        raise HTTPException(401, 'Phiên xác thực đã hết hạn hoặc bị thu hồi. Hãy đăng nhập lại.')
    _require_fresh_otp(request)
    if aware(row.expires_at) <= now():
        raise HTTPException(400, 'Phiên chụp đã hết hạn. Hãy bắt đầu thiết lập lại.')
    # The account lock also serializes concurrent enrollments at the cap.
    if len(db.scalars(select(BiometricDevice.id).where(BiometricDevice.user_id == user.id,
            BiometricDevice.revoked == False, BiometricDevice.expires_at > now())).all()) >= 10:
        raise HTTPException(409, 'Đã đạt giới hạn thiết bị sinh trắc học.')
    device = BiometricDevice(id=row.device_id, user_id=user.id, kind=row.kind,
        device_name=row.device_name, public_key=canonical, key_fingerprint=fingerprint,
        face_template=template, created_at=now(), expires_at=now() + timedelta(days=DEVICE_DAYS))
    db.add(device)
    _audit(db, user.id, 'Bật đăng nhập sinh trắc học', device.id, {'kind': device.kind, 'device_name': device.device_name})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Thiết lập đã tồn tại. Hãy tải lại cài đặt.')
    return {'device': _device_view(device)}


@router.post('/auth/biometric/challenge')
def login_challenge(data: schemas.BiometricLoginChallenge, request: Request, db: Session = Depends(get_db)):
    host = request.client.host if request.client else 'unknown'
    security.throttle(db, f'biometric-ip:{host}', limit=24)
    security.throttle(db, f'biometric-device:{data.device_id}', limit=12)
    device, user = _load_device(db, data.device_id)
    if device.kind == 'face' and not face_ready():
        raise HTTPException(503, 'Nhận diện khuôn mặt chưa sẵn sàng. Hãy dùng mật khẩu và OTP.')
    return _challenge_view(_new_challenge(db, user.id, device.id, device.kind, 'login'))


@router.post('/auth/biometric/verify')
def verify(data: schemas.BiometricProof, request: Request, db: Session = Depends(get_db)):
    host = request.client.host if request.client else 'unknown'
    security.throttle(db, f'biometric-verify-ip:{host}', limit=30)
    row = _load_challenge(db, data.challenge_id, 'login')
    _consume(db, row)
    device, user = _load_device(db, row.device_id)
    images = _decode_images(data.images)
    if row.user_id != user.id or row.kind != device.kind or not _verify_signature(device.public_key, data.signature, row.payload, images):
        raise HTTPException(401, LOGIN_FAILURE)
    if device.kind == 'fingerprint' and images:
        raise HTTPException(401, LOGIN_FAILURE)
    if device.kind == 'face':
        if len(images) != len(row.steps) or (now() - aware(row.issued_at)).total_seconds() < 2:
            raise HTTPException(401, LOGIN_FAILURE)
        templates = _decrypt_template(device.face_template, user.id, device.id)
        _face_call('verify_faces', images, row.steps, templates)
    device.last_used_at = now()
    _audit(db, user.id, 'Đăng nhập sinh trắc học', device.id, {'kind': device.kind})
    token = security.create_session(db, user, method=device.kind, device_id=device.id)
    return {'access_token': token, 'token_type': 'bearer', 'user': public(user), 'auth_method': device.kind}


@router.delete('/me/biometric-devices/{id}')
def revoke_device(id: str, request: Request, user=Depends(security.current_user), db: Session = Depends(get_db)):
    device = db.scalar(select(BiometricDevice).where(BiometricDevice.id == id).with_for_update())
    if device is None or device.user_id != user.id:
        raise HTTPException(404, 'Không tìm thấy thiết lập sinh trắc học của bạn.')
    device.revoked, device.face_template = True, None
    session_ids = select(BiometricSessionLink.session_id).where(BiometricSessionLink.device_id == device.id)
    db.execute(update(AuthSession).where(AuthSession.id.in_(session_ids)).values(revoked=True))
    current_revoked = request.state.auth_claims.get('device_id') == device.id
    _audit(db, user.id, 'Thu hồi đăng nhập sinh trắc học', device.id, {'kind': device.kind, 'device_name': device.device_name})
    db.commit()
    return {'revoked': True, 'current_session_revoked': current_revoked}
