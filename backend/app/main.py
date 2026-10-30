import csv
import io
import math
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from . import config, schemas as s, security as sec, mailer, biometric
from .db import (Base, engine, get_db, SessionLocal, now, aware, public, User, Challenge,
    AuthSession, BiometricDevice, BiometricChallenge, BiometricSessionLink,
    Site, Shift, Assignment, Attendance, Correction, Audit)

VN = timezone(timedelta(hours=7))

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    # Optional first-admin bootstrap; no hardcoded demo credentials.
    if os.getenv('ADMIN_EMAIL') and os.getenv('ADMIN_PASSWORD'):
        with SessionLocal() as db:
            if not db.scalar(select(User).where(User.role == 'admin')):
                username = os.getenv('ADMIN_USERNAME', 'tranvanvu').lower()
                data = s.Register(username=username, email=os.environ['ADMIN_EMAIL'],
                    password=os.environ['ADMIN_PASSWORD'], full_name='Trần Văn Vũ')
                db.add(User(**data.model_dump(exclude={'password'}), role='admin',
                    password_hash=sec.passwords.hash(data.password), verified=False))
                db.commit()
    yield

app = FastAPI(title='TranVanVu_2380602601 • API chấm công', version='1.0.0', lifespan=lifespan)
app.add_middleware(biometric.BiometricBodyLimitMiddleware)
app.include_router(biometric.router)

@app.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    # Never echo password/OTP values from validation errors.
    fields = ', '.join(dict.fromkeys(str(e['loc'][-1]) for e in exc.errors()))
    return JSONResponse(status_code=422, content={'detail': f'Dữ liệu chưa hợp lệ: {fields}. Vui lòng kiểm tra lại.'})

def save(db):
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Dữ liệu trùng hoặc đang được tham chiếu. Vui lòng tải lại và kiểm tra.')

def get_or_404(db, model, id):
    item = db.get(model, id)
    if item is None: raise HTTPException(404, 'Không tìm thấy dữ liệu.')
    return item

def audit(db, user, action, id, details=None):
    db.add(Audit(user_id=user.id, action=action, entity_id=id, details=details or {}))

def shift_window(assignment, shift):
    start = datetime.combine(date.fromisoformat(assignment.work_date), time.fromisoformat(shift.start_time), VN)
    end = datetime.combine(date.fromisoformat(assignment.work_date), time.fromisoformat(shift.end_time), VN)
    if end <= start: end += timedelta(days=1)
    return start, end

def assignment_view(db, item):
    result = public(item)
    shift, user = db.get(Shift, item.shift_id), db.get(User, item.user_id)
    result['shift'] = public(shift)
    result['site'] = public(db.get(Site, shift.site_id))
    result['employee_name'] = user.full_name
    attendance = db.scalar(select(Attendance).where(Attendance.assignment_id == item.id))
    result['attendance'] = public(attendance) if attendance else None
    return result

def correction_view(db, row):
    return {**public(row), 'employee_name': db.get(User, row.user_id).full_name,
        'assignment': assignment_view(db, db.get(Assignment, row.assignment_id))}

def distance_m(lat1, lon1, lat2, lon2):
    a1, a2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = a2-a1, math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(a1)*math.cos(a2)*math.sin(dlon/2)**2
    return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0, 1-a)))

def evidence_report(data, site):
    distance = distance_m(data.latitude, data.longitude, site.latitude, site.longitude)
    flags = []
    if data.is_mocked: flags.append('Thiết bị báo vị trí mô phỏng')
    if data.accuracy_m > 100: flags.append('GPS chưa đủ chính xác (trên 100 m)')
    if distance > site.radius_m: flags.append('Ngoài bán kính chấm công')
    if abs((now() - data.captured_at).total_seconds()) > 90: flags.append('Mẫu vị trí quá cũ hoặc sai giờ thiết bị')
    token_valid = False
    try:
        qr = sec.decode(data.qr_token, 'site_qr')
        token_valid = qr.get('site_id') == site.id and qr.get('version') == site.qr_version
    except HTTPException: pass
    if not token_valid: flags.append('QR hết hạn hoặc không thuộc điểm chấm công')
    # This is evidence, not a claim of cryptographic device attestation or anti-spoofing.
    motion_label = 'Ít chuyển động' if data.motion_rms < 0.3 else ('Đang di chuyển' if data.motion_rms < 3 else 'Chuyển động mạnh')
    return {'latitude': data.latitude, 'longitude': data.longitude,
        'accuracy_m': data.accuracy_m, 'distance_m': round(distance, 1),
        'is_mocked': data.is_mocked, 'captured_at': data.captured_at.isoformat(),
        'motion_rms': round(data.motion_rms, 3), 'motion_samples': data.motion_samples,
        'motion_duration_ms': data.motion_duration_ms, 'motion_label': motion_label,
        'qr_valid': token_valid, 'flags': flags, 'accepted': not flags}

@app.get('/health')
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    if config.EMAIL_TRANSPORT == 'apps_script':
        configured = bool(os.getenv('GAS_WEBHOOK_URL') and len(os.getenv('GAS_SHARED_SECRET', '')) >= 32)
    elif config.EMAIL_TRANSPORT == 'resend':
        configured = bool(os.getenv('RESEND_API_KEY') and os.getenv('MAIL_FROM'))
    else:
        configured = bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD') and os.getenv('MAIL_FROM'))
    return {'status': 'ok', 'project': 'TranVanVu_2380602601', 'email_configured': configured,
            'server_time': now().isoformat(), 'security_version': '2',
            'face_ready': biometric.face_ready()}

@app.post('/auth/register', status_code=201)
def register(data: s.Register, request: Request, db: Session = Depends(get_db)):
    sec.throttle(db, f'register:{request.client.host}', limit=15)
    existing = db.scalar(select(User).where(or_(User.username == data.username, User.email == data.email)))
    if existing:
        if existing.verified or existing.email != data.email or existing.username != data.username or not sec.passwords.verify(data.password, existing.password_hash):
            raise HTTPException(409, 'Tên đăng nhập hoặc email đã được sử dụng.')
        user = existing
    else:
        user = User(**data.model_dump(exclude={'password'}), password_hash=sec.passwords.hash(data.password))
        db.add(user)
        save(db)
    return sec.issue_challenge(db, user, 'register')

@app.post('/auth/login')
def login(data: s.Login, request: Request, db: Session = Depends(get_db)):
    sec.throttle(db, f'login:{request.client.host}:{data.username.lower()}', limit=8)
    sec.throttle(db, f'login-ip:{request.client.host}', limit=60)
    user = db.scalar(select(User).where(or_(User.username == data.username.lower(), User.email == data.username.lower())))
    ok = sec.passwords.verify(data.password, user.password_hash if user else sec.dummy_hash)
    if not user or not ok or not user.active:
        raise HTTPException(401, 'Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa.')
    return sec.issue_challenge(db, user, 'login')

@app.post('/auth/verify')
def verify(data: s.Verify, db: Session = Depends(get_db)):
    row = db.scalar(select(Challenge).where(Challenge.id == data.challenge_id).with_for_update())
    if not row or row.used or aware(row.expires_at) <= now() or row.attempts >= 5:
        raise HTTPException(400, 'Mã đã hết hạn, đã dùng hoặc đã nhập sai 5 lần.')
    row.attempts += 1
    if not __import__('hmac').compare_digest(row.code_hash, sec.code_hash(row.id, data.code)):
        save(db)
        raise HTTPException(400, f'Mã OTP chưa đúng. Còn {5-row.attempts} lần thử.')
    user = get_or_404(db, User, row.user_id)
    if not user.active: raise HTTPException(403, 'Tài khoản đã bị khóa.')
    row.used, user.verified = True, True
    save(db)
    if row.purpose == 'register': return {'message': 'Đã xác thực email. Bạn có thể đăng nhập.'}
    return {'access_token': sec.create_session(db, user), 'token_type': 'bearer',
            'user': public(user), 'auth_method': 'password_otp'}

@app.post('/auth/resend')
def resend(data: s.Resend, db: Session = Depends(get_db)):
    row = db.scalar(select(Challenge).where(Challenge.id == data.challenge_id).with_for_update())
    if not row or row.used or row.attempts >= 5 or row.resends >= 3:
        raise HTTPException(400, 'Vui lòng thực hiện lại đăng ký hoặc đăng nhập để nhận mã mới.')
    if (now() - aware(row.issued_at)).total_seconds() < 60:
        raise HTTPException(429, 'Vui lòng đợi 60 giây giữa hai lần gửi.')
    code = f'{__import__("secrets").randbelow(1000000):06d}'
    user = get_or_404(db, User, row.user_id)
    try: mailer.send_otp(user.email, code)
    except Exception: raise HTTPException(503, 'Gửi email thất bại. Vui lòng thử lại sau.')
    row.code_hash, row.issued_at, row.expires_at = sec.code_hash(row.id, code), now(), now() + timedelta(seconds=config.OTP_SECONDS)
    row.resends += 1
    save(db)
    return sec.challenge_response(row, user)

@app.post('/auth/logout')
def logout(request: Request, user=Depends(sec.current_user), db: Session = Depends(get_db)):
    db.get(AuthSession, request.state.auth_session_id).revoked = True
    save(db)
    return {'message': 'Đã đăng xuất.'}

@app.get('/me')
def me(user=Depends(sec.current_user)): return public(user)

@app.put('/me')
def profile(data: s.ProfileEdit, user=Depends(sec.current_user), db: Session = Depends(get_db)):
    for key, value in data.model_dump().items(): setattr(user, key, value)
    save(db)
    return public(user)

@app.get('/employees')
def employees(user=Depends(sec.admin), db: Session = Depends(get_db)):
    return [public(x) for x in db.scalars(select(User).order_by(User.created_at.desc()))]

@app.post('/employees', status_code=201)
def create_employee(data: s.Register, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = User(**data.model_dump(exclude={'password'}), password_hash=sec.passwords.hash(data.password))
    db.add(row)
    try: db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Tên đăng nhập hoặc email đã tồn tại.')
    audit(db, user, 'Tạo nhân viên', row.id)
    save(db)
    return public(row)

@app.put('/employees/{id}')
def edit_employee(id: str, data: s.EmployeeEdit, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = get_or_404(db, User, id)
    if id == user.id and (not data.active or data.role != 'admin'):
        raise HTTPException(400, 'Không thể tự khóa hoặc tự hạ quyền tài khoản quản trị đang dùng.')
    for key, value in data.model_dump().items(): setattr(row, key, value)
    if not row.active:
        db.execute(update(AuthSession).where(AuthSession.user_id == id).values(revoked=True))
        db.execute(update(BiometricDevice).where(BiometricDevice.user_id == id)
                   .values(revoked=True, face_template=None))
    audit(db, user, 'Sửa nhân viên', id, {'role': data.role, 'active': data.active})
    save(db)
    return public(row)

@app.delete('/employees/{id}')
def delete_employee(id: str, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = get_or_404(db, User, id)
    if id == user.id: raise HTTPException(400, 'Không thể xóa tài khoản đang sử dụng.')
    if db.scalar(select(Assignment.id).where(Assignment.user_id == id)) or db.scalar(select(Audit.id).where(Audit.user_id == id)):
        raise HTTPException(409, 'Nhân viên có lịch sử. Hãy khóa tài khoản để giữ dữ liệu chấm công.')
    device_ids = select(BiometricDevice.id).where(BiometricDevice.user_id == id)
    for link in db.scalars(select(BiometricSessionLink).where(BiometricSessionLink.device_id.in_(device_ids))):
        db.delete(link)
    db.flush()
    for model in (BiometricChallenge, BiometricDevice, Challenge, AuthSession):
        for child in db.scalars(select(model).where(model.user_id == id)): db.delete(child)
    db.delete(row)
    audit(db, user, 'Xóa nhân viên', id)
    save(db)
    return {'message': 'Đã xóa nhân viên.'}

@app.get('/sites')
def sites(user=Depends(sec.current_user), db: Session = Depends(get_db)):
    return [public(x) for x in db.scalars(select(Site).order_by(Site.name))]

@app.post('/sites', status_code=201)
def create_site(data: s.SiteData, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = Site(**data.model_dump()); db.add(row); db.flush()
    audit(db, user, 'Tạo điểm chấm công', row.id); save(db)
    return public(row)

@app.put('/sites/{id}')
def edit_site(id: str, data: s.SiteData, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = get_or_404(db, Site, id)
    for key, value in data.model_dump().items(): setattr(row, key, value)
    row.qr_version += 1
    audit(db, user, 'Sửa điểm chấm công', id); save(db)
    return public(row)

@app.delete('/sites/{id}')
def delete_site(id: str, user=Depends(sec.admin), db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Site, id)); audit(db, user, 'Xóa điểm chấm công', id); save(db)
    return {'message': 'Đã xóa điểm chấm công.'}

@app.get('/sites/{id}/qr')
def site_qr(id: str, user=Depends(sec.admin), db: Session = Depends(get_db)):
    site = get_or_404(db, Site, id)
    return {'token': sec.signed({'site_id': site.id, 'version': site.qr_version}, 90, 'site_qr'),
        'expires_in': 90, 'site_name': site.name}

@app.get('/shifts')
def shifts(user=Depends(sec.current_user), db: Session = Depends(get_db)):
    return [{**public(x), 'site_name': db.get(Site, x.site_id).name} for x in db.scalars(select(Shift).order_by(Shift.start_time))]

@app.post('/shifts', status_code=201)
def create_shift(data: s.ShiftData, user=Depends(sec.admin), db: Session = Depends(get_db)):
    get_or_404(db, Site, data.site_id)
    row = Shift(**data.model_dump()); db.add(row); db.flush()
    audit(db, user, 'Tạo ca làm', row.id); save(db)
    return public(row)

@app.put('/shifts/{id}')
def edit_shift(id: str, data: s.ShiftData, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = get_or_404(db, Shift, id); get_or_404(db, Site, data.site_id)
    if db.scalar(select(Attendance.id).join(Assignment, Assignment.id == Attendance.assignment_id).where(Assignment.shift_id == id)):
        raise HTTPException(409, 'Ca đã có chấm công. Hãy tạo ca mới để bảo toàn lịch sử.')
    for key, value in data.model_dump().items(): setattr(row, key, value)
    audit(db, user, 'Sửa ca làm', id); save(db)
    return public(row)

@app.delete('/shifts/{id}')
def delete_shift(id: str, user=Depends(sec.admin), db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Shift, id)); audit(db, user, 'Xóa ca làm', id); save(db)
    return {'message': 'Đã xóa ca làm.'}

def check_assignment_data(db, data, exclude=None):
    employee, shift = get_or_404(db, User, data.user_id), get_or_404(db, Shift, data.shift_id)
    db.scalar(select(User).where(User.id == employee.id).with_for_update())
    if not employee.active: raise HTTPException(400, 'Nhân viên đã bị khóa.')
    proposed = Assignment(user_id=data.user_id, shift_id=data.shift_id, work_date=data.work_date.isoformat())
    start, end = shift_window(proposed, shift)
    candidates = db.scalars(select(Assignment).where(Assignment.user_id == employee.id,
        Assignment.work_date >= (data.work_date-timedelta(days=1)).isoformat(),
        Assignment.work_date <= (data.work_date+timedelta(days=1)).isoformat()))
    for other in candidates:
        if other.id == exclude: continue
        a, b = shift_window(other, db.get(Shift, other.shift_id))
        if start < b and end > a: raise HTTPException(409, 'Nhân viên đã có ca làm trùng thời gian.')

@app.get('/assignments')
def assignments(user=Depends(sec.current_user), db: Session = Depends(get_db)):
    query = select(Assignment).order_by(Assignment.work_date.desc()).limit(1000)
    if user.role != 'admin': query = query.where(Assignment.user_id == user.id)
    return [assignment_view(db, x) for x in db.scalars(query)]

@app.post('/assignments', status_code=201)
def create_assignment(data: s.AssignmentData, user=Depends(sec.admin), db: Session = Depends(get_db)):
    check_assignment_data(db, data)
    row = Assignment(**data.model_dump(mode='json')); db.add(row); db.flush()
    audit(db, user, 'Phân ca', row.id); save(db)
    return assignment_view(db, row)

@app.put('/assignments/{id}')
def edit_assignment(id: str, data: s.AssignmentData, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = get_or_404(db, Assignment, id)
    if db.scalar(select(Attendance.id).where(Attendance.assignment_id == id)) or db.scalar(select(Correction.id).where(Correction.assignment_id == id)):
        raise HTTPException(409, 'Phân ca đã có lịch sử, không thể đổi.')
    check_assignment_data(db, data, id)
    for key, value in data.model_dump(mode='json').items(): setattr(row, key, value)
    audit(db, user, 'Sửa phân ca', id); save(db)
    return assignment_view(db, row)

@app.delete('/assignments/{id}')
def delete_assignment(id: str, user=Depends(sec.admin), db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Assignment, id)); audit(db, user, 'Xóa phân ca', id); save(db)
    return {'message': 'Đã xóa phân ca.'}

@app.post('/attendance/check')
def check(data: s.CheckData, user=Depends(sec.current_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(Assignment).where(Assignment.id == data.assignment_id).with_for_update())
    if not assignment: raise HTTPException(404, 'Không tìm thấy ca làm.')
    if assignment.user_id != user.id: raise HTTPException(403, 'Chỉ được chấm công cho chính mình.')
    shift = db.get(Shift, assignment.shift_id)
    site = db.get(Site, shift.site_id)
    start, end = shift_window(assignment, shift)
    if now() < start - timedelta(hours=2) or now() > end + timedelta(hours=4):
        raise HTTPException(400, 'Ngoài khung giờ chấm công của ca. Hãy gửi yêu cầu giải trình nếu cần.')
    report = evidence_report(data, site)
    if report['flags']:
        raise HTTPException(400, {'message': 'Chưa đủ điều kiện chấm công.', 'evidence': report})
    attendance = db.scalar(select(Attendance).where(Attendance.assignment_id == assignment.id).with_for_update())
    if data.action == 'in':
        if attendance and attendance.check_in: raise HTTPException(409, 'Bạn đã chấm công vào ca này.')
        if attendance is None:
            attendance = Attendance(assignment_id=assignment.id); db.add(attendance)
        attendance.check_in, attendance.in_evidence = now(), report
        attendance.status = 'late' if now() > start + timedelta(minutes=shift.grace_minutes) else 'present'
    else:
        if not attendance or not attendance.check_in: raise HTTPException(400, 'Cần chấm công vào trước khi ra.')
        if attendance.check_out: raise HTTPException(409, 'Bạn đã chấm công ra ca này.')
        attendance.check_out, attendance.out_evidence = now(), report
    audit(db, user, 'Chấm công vào' if data.action == 'in' else 'Chấm công ra', assignment.id, report)
    save(db)
    return public(attendance)

@app.get('/corrections')
def corrections(user=Depends(sec.current_user), db: Session = Depends(get_db)):
    query = select(Correction).order_by(Correction.created_at.desc()).limit(1000)
    if user.role != 'admin': query = query.where(Correction.user_id == user.id)
    return [correction_view(db, x) for x in db.scalars(query)]

def validate_correction(db, data, user):
    assignment = get_or_404(db, Assignment, data.assignment_id)
    if assignment.user_id != user.id: raise HTTPException(403, 'Chỉ được gửi yêu cầu cho ca của bạn.')
    start, end = shift_window(assignment, db.get(Shift, assignment.shift_id))
    if data.requested_in < start-timedelta(hours=2) or data.requested_in > end+timedelta(hours=4):
        raise HTTPException(400, 'Giờ đề xuất không thuộc ngày và khung giờ ca làm.')
    if data.requested_in > now() or (data.requested_out and data.requested_out > now()):
        raise HTTPException(400, 'Không thể đề xuất chấm công trong tương lai.')
    if data.requested_out and data.requested_out > end+timedelta(hours=4):
        raise HTTPException(400, 'Giờ ra đề xuất quá xa thời gian kết thúc ca.')
    return assignment

@app.post('/corrections', status_code=201)
def create_correction(data: s.CorrectionData, user=Depends(sec.current_user), db: Session = Depends(get_db)):
    assignment = validate_correction(db, data, user)
    if db.scalar(select(Correction.id).where(Correction.assignment_id == data.assignment_id, Correction.status == 'pending')):
        raise HTTPException(409, 'Ca này đã có yêu cầu đang chờ duyệt.')
    report = None
    if data.evidence:
        shift = db.get(Shift, assignment.shift_id)
        report = evidence_report(data.evidence, db.get(Site, shift.site_id))
    row = Correction(**data.model_dump(exclude={'evidence'}), user_id=user.id, evidence=report)
    db.add(row); db.flush(); audit(db, user, 'Gửi giải trình', row.id); save(db)
    return correction_view(db, row)

@app.put('/corrections/{id}')
def edit_correction(id: str, data: s.CorrectionData, user=Depends(sec.current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Correction).where(Correction.id == id).with_for_update())
    if not row: raise HTTPException(404, 'Không tìm thấy yêu cầu.')
    if row.user_id != user.id: raise HTTPException(403, 'Yêu cầu không thuộc tài khoản của bạn.')
    if row.status != 'pending': raise HTTPException(409, 'Chỉ được sửa yêu cầu đang chờ duyệt.')
    if row.assignment_id != data.assignment_id: raise HTTPException(400, 'Không thể đổi ca của yêu cầu.')
    assignment = validate_correction(db, data, user)
    for key, value in data.model_dump(exclude={'evidence'}).items(): setattr(row, key, value)
    if data.evidence:
        row.evidence = evidence_report(data.evidence, db.get(Site, db.get(Shift, assignment.shift_id).site_id))
    audit(db, user, 'Sửa giải trình', id); save(db)
    return correction_view(db, row)

@app.delete('/corrections/{id}')
def delete_correction(id: str, user=Depends(sec.current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Correction).where(Correction.id == id).with_for_update())
    if not row: raise HTTPException(404, 'Không tìm thấy yêu cầu.')
    if row.user_id != user.id: raise HTTPException(403, 'Yêu cầu không thuộc tài khoản của bạn.')
    if row.status != 'pending': raise HTTPException(409, 'Chỉ được xóa yêu cầu đang chờ duyệt.')
    db.delete(row); audit(db, user, 'Xóa giải trình', id); save(db)
    return {'message': 'Đã xóa yêu cầu.'}

@app.post('/corrections/{id}/review')
def review(id: str, data: s.Review, user=Depends(sec.admin), db: Session = Depends(get_db)):
    row = db.scalar(select(Correction).where(Correction.id == id).with_for_update())
    if not row: raise HTTPException(404, 'Không tìm thấy yêu cầu.')
    if row.status != 'pending': raise HTTPException(409, 'Yêu cầu đã được xử lý.')
    if row.user_id == user.id: raise HTTPException(403, 'Không được tự duyệt yêu cầu của mình.')
    row.status, row.review_note, row.reviewed_by = data.decision, data.note, user.id
    if data.decision == 'approved':
        assignment = db.scalar(select(Assignment).where(Assignment.id == row.assignment_id).with_for_update())
        attendance = db.scalar(select(Attendance).where(Attendance.assignment_id == row.assignment_id))
        if not attendance:
            attendance = Attendance(assignment_id=row.assignment_id); db.add(attendance)
        start, _ = shift_window(assignment, db.get(Shift, assignment.shift_id))
        previous = public(attendance) if attendance.id else {}
        attendance.check_in, attendance.check_out = row.requested_in, row.requested_out
        attendance.status = 'adjusted'
        audit(db, user, 'Duyệt điều chỉnh chấm công', row.assignment_id,
            {'previous': previous, 'correction_id': id, 'note': data.note})
    audit(db, user, 'Duyệt giải trình', id, data.model_dump()); save(db)
    return correction_view(db, row)

@app.get('/dashboard')
def dashboard(user=Depends(sec.current_user), db: Session = Depends(get_db)):
    today = now().astimezone(VN).date().isoformat()
    query = select(Assignment).where(Assignment.work_date >= (now().astimezone(VN).date()-timedelta(days=1)).isoformat(), Assignment.work_date <= today)
    if user.role != 'admin': query = query.where(Assignment.user_id == user.id)
    rows = [assignment_view(db, x) for x in db.scalars(query)]
    pending = select(func.count()).select_from(Correction).where(Correction.status == 'pending')
    if user.role != 'admin': pending = pending.where(Correction.user_id == user.id)
    todays = [x for x in rows if x['work_date'] == today]
    return {'date': today, 'server_time': now().isoformat(), 'assignments': rows,
        'scheduled': len(todays), 'checked_in': sum(bool(x['attendance'] and x['attendance']['check_in']) for x in todays),
        'late': sum(bool(x['attendance'] and x['attendance']['status'] == 'late') for x in todays),
        'pending': db.scalar(pending),
        'employees': db.scalar(select(func.count()).select_from(User).where(User.active == True)) if user.role == 'admin' else None}

@app.get('/audit')
def audit_logs(user=Depends(sec.admin), db: Session = Depends(get_db)):
    return [{**public(x), 'actor_name': db.get(User, x.user_id).full_name} for x in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(300))]

@app.get('/reports/csv')
def csv_report(user=Depends(sec.admin), db: Session = Depends(get_db)):
    buffer = io.StringIO(); writer = csv.writer(buffer)
    writer.writerow(['Nhân viên', 'Tên đăng nhập', 'Ngày', 'Ca', 'Vào (GMT+7)', 'Ra (GMT+7)', 'Giờ công', 'Trạng thái'])
    def safe(value):
        value = str(value)
        return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value
    for assignment in db.scalars(select(Assignment).order_by(Assignment.work_date.desc()).limit(10000)):
        employee, shift = db.get(User, assignment.user_id), db.get(Shift, assignment.shift_id)
        attendance = db.scalar(select(Attendance).where(Attendance.assignment_id == assignment.id))
        check_in = aware(attendance.check_in) if attendance and attendance.check_in else None
        check_out = aware(attendance.check_out) if attendance and attendance.check_out else None
        hours = round((check_out-check_in).total_seconds()/3600, 2) if check_in and check_out else ''
        writer.writerow([safe(employee.full_name), safe(employee.username), assignment.work_date, safe(shift.name),
            check_in.astimezone(VN).strftime('%d/%m/%Y %H:%M') if check_in else '',
            check_out.astimezone(VN).strftime('%d/%m/%Y %H:%M') if check_out else '', hours,
            attendance.status if attendance else 'Chưa chấm công'])
    return Response('\ufeff' + buffer.getvalue(), media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="TranVanVu_2380602601_chamcong.csv"'})
