from datetime import timedelta
from sqlalchemy import select
from app.db import SessionLocal, User, Challenge, Attendance, Site, AuthSession
from app import security, mailer
from conftest import headers, evidence, PASSWORD

def test_registration_email_otp_and_password_otp_login(client):
    data = {'username':'new_staff','email':'new@example.com','full_name':'Nhân viên mới','password':PASSWORD}
    response = client.post('/auth/register', json=data)
    assert response.status_code == 201
    assert 'code' not in response.json() and 'access_token' not in response.json()
    challenge = response.json()['challenge_id']
    assert client.post('/auth/verify',json={'challenge_id':challenge,'code':client.codes[data['email']]}).status_code == 200
    with SessionLocal() as db:
        row = db.scalar(select(Challenge).where(Challenge.id == challenge))
        row.issued_at = client.fixed-timedelta(seconds=61)
        db.commit()
    response = client.post('/auth/login', json={'username':'new_staff','password':PASSWORD})
    assert 'access_token' not in response.json()
    verified = client.post('/auth/verify',json={'challenge_id':response.json()['challenge_id'],'code':client.codes[data['email']]})
    assert verified.status_code == 200
    token = verified.json()['access_token']
    me = client.get('/me',headers={'Authorization':f'Bearer {token}'})
    assert me.json()['role'] == 'employee' and 'password_hash' not in me.json()
    assert client.post('/auth/verify',json={'challenge_id':response.json()['challenge_id'],'code':client.codes[data['email']]}).status_code == 400

def test_cannot_register_as_admin(client):
    r=client.post('/auth/register',json={'username':'evil','email':'evil@example.com','full_name':'Attacker','password':PASSWORD,'role':'admin'})
    assert r.status_code==422
    assert PASSWORD not in r.text

def test_otp_five_attempts_lock(client):
    r=client.post('/auth/login',json={'username':'employee','password':PASSWORD})
    id=r.json()['challenge_id']
    code=client.codes['employee@example.com']
    wrong='000000' if code!='000000' else '111111'
    for _ in range(5): assert client.post('/auth/verify',json={'challenge_id':id,'code':wrong}).status_code==400
    assert client.post('/auth/verify',json={'challenge_id':id,'code':code}).status_code==400

def test_otp_expiration(client):
    r=client.post('/auth/login',json={'username':'employee','password':PASSWORD})
    with SessionLocal() as db:
        row=db.get(Challenge,r.json()['challenge_id']);row.expires_at=client.fixed-timedelta(seconds=1);db.commit()
    assert client.post('/auth/verify',json={'challenge_id':r.json()['challenge_id'],'code':client.codes['employee@example.com']}).status_code==400

def test_email_failure_never_returns_token(client,monkeypatch):
    def fail(*args): raise RuntimeError('SMTP unavailable')
    monkeypatch.setattr(mailer,'send_otp',fail)
    r=client.post('/auth/login',json={'username':'employee','password':PASSWORD})
    assert r.status_code==503 and 'access_token' not in r.json()

def test_login_rate_limit(client):
    for _ in range(8):assert client.post('/auth/login',json={'username':'employee','password':'bad'}).status_code==401
    assert client.post('/auth/login',json={'username':'employee','password':PASSWORD}).status_code==429

def test_employee_forbidden_admin_routes(client):
    h=headers('employee')
    for path in ['/employees','/sites/site/qr','/audit','/reports/csv']:
        assert client.get(path,headers=h).status_code==403
    assert client.post('/sites',headers=h,json={'name':'Site','latitude':10,'longitude':106,'radius_m':150}).status_code==403
    assert all(x['user_id']=='employee' for x in client.get('/assignments',headers=h).json())
    assert client.get('/employees').status_code==401

def test_logout_revokes_token(client):
    h=headers('employee');assert client.post('/auth/logout',headers=h).status_code==200
    assert client.get('/me',headers=h).status_code==401

def test_disable_account_revokes_sessions(client):
    a,e=headers('admin'),headers('employee')
    assert client.put('/employees/employee',headers=a,json={'full_name':'Employee','role':'employee','active':False}).status_code==200
    assert client.get('/me',headers=e).status_code==401

def test_site_full_crud_and_foreign_keys(client):
    h=headers('admin');data={'name':'Điểm mới','latitude':10.8,'longitude':106.7,'radius_m':150}
    r=client.post('/sites',headers=h,json=data);assert r.status_code==201
    id=r.json()['id'];assert any(x['id']==id for x in client.get('/sites',headers=h).json())
    assert client.put(f'/sites/{id}',headers=h,json={**data,'name':'Đã sửa'}).json()['name']=='Đã sửa'
    assert client.delete(f'/sites/{id}',headers=h).status_code==200
    assert client.delete('/sites/site',headers=h).status_code==409
    assert client.get('/sites',headers=h).status_code==200

def test_employee_create_update_delete(client):
    h=headers('admin');r=client.post('/employees',headers=h,json={'username':'temporary','email':'temp@example.com','full_name':'Tạm thời','password':PASSWORD})
    assert r.status_code==201
    id=r.json()['id'];assert r.json()['verified'] is False
    assert client.put(f'/employees/{id}',headers=h,json={'full_name':'Mới','department':'IT','role':'employee','active':True}).status_code==200
    assert client.delete(f'/employees/{id}',headers=h).status_code==200
    assert client.delete('/employees/admin',headers=h).status_code==400

def test_checkin_checkout_and_duplicate(client):
    a,e=headers('admin'),headers('employee');data=evidence(client,a)
    response=client.post('/attendance/check',headers=e,json=data)
    assert response.status_code==200 and response.json()['status']=='late'
    assert response.json()['in_evidence']['accepted'] is True
    assert client.post('/attendance/check',headers=e,json=data).status_code==409
    assert client.post('/attendance/check',headers=e,json={**data,'action':'out'}).status_code==200
    assert client.post('/attendance/check',headers=e,json={**data,'action':'out'}).status_code==409

def test_cannot_checkin_for_other_employee(client):
    assert client.post('/attendance/check',headers=headers('other'),json=evidence(client,headers('admin'))).status_code==403

def test_checkout_requires_checkin(client):
    assert client.post('/attendance/check',headers=headers('employee'),json={**evidence(client,headers('admin')),'action':'out'}).status_code==400

def test_reject_outside_mock_low_accuracy_stale_gps(client):
    a,e=headers('admin'),headers('employee');base=evidence(client,a)
    for change in [{'latitude':11},{'is_mocked':True},{'accuracy_m':200},
        {'captured_at':(client.fixed-timedelta(minutes=10)).isoformat()}]:
        r=client.post('/attendance/check',headers=e,json={**base,**change})
        assert r.status_code==400 and r.json()['detail']['evidence']['flags']
    with SessionLocal() as db:assert db.scalar(select(Attendance)) is None

def test_wrong_expired_or_wrong_type_qr(client):
    a,e=headers('admin'),headers('employee');base=evidence(client,a)
    tokens=[security.signed({'site_id':'site','version':1},-60,'site_qr'),
      security.signed({'site_id':'other','version':1},90,'site_qr'),
      security.signed({'site_id':'site','version':1},90,'access')]
    for token in tokens:assert client.post('/attendance/check',headers=e,json={**base,'qr_token':token}).status_code==400

def test_site_edit_revokes_existing_qr(client):
    a,e=headers('admin'),headers('employee');base=evidence(client,a)
    client.put('/sites/site',headers=a,json={'name':'Văn phòng sửa','latitude':10.8,'longitude':106.7,'radius_m':150})
    assert client.post('/attendance/check',headers=e,json=base).status_code==400

def test_insufficient_motion_and_nan_rejected(client):
    base=evidence(client,headers('admin'));e=headers('employee')
    for change in [{'motion_samples':0},{'motion_duration_ms':100},{'latitude':'NaN'}]:
        assert client.post('/attendance/check',headers=e,json={**base,**change}).status_code==422

def test_shift_overnight_and_overlap(client):
    a=headers('admin');r=client.post('/shifts',headers=a,json={'name':'Ca đêm','site_id':'site','start_time':'22:00','end_time':'06:00','grace_minutes':10})
    assert r.status_code==201
    assert client.post('/assignments',headers=a,json={'user_id':'employee','shift_id':r.json()['id'],'work_date':'2026-10-29'}).status_code==409
    assert client.post('/assignments',headers=a,json={'user_id':'other','shift_id':r.json()['id'],'work_date':'2026-10-29'}).status_code==201

def test_correction_ownership_review_and_audit(client):
    a,e,o=headers('admin'),headers('employee'),headers('other')
    base={'assignment_id':'assignment','requested_in':'2026-10-29T07:00:00Z','requested_out':None,'reason':'GPS trong nhà bị lệch vị trí'}
    assert client.post('/corrections',headers=o,json=base).status_code==403
    raw=evidence(client,a);raw.pop('assignment_id');raw.pop('action')
    r=client.post('/corrections',headers=e,json={**base,'evidence':raw});assert r.status_code==201
    id=r.json()['id'];assert r.json()['evidence']['qr_valid'] is True
    assert client.put(f'/corrections/{id}',headers=o,json=base).status_code==403
    assert client.post(f'/corrections/{id}/review',headers=e,json={'decision':'approved','note':'Đồng ý'}).status_code==403
    assert client.post(f'/corrections/{id}/review',headers=a,json={'decision':'approved','note':'Đã kiểm tra tại văn phòng'}).status_code==200
    assert client.put(f'/corrections/{id}',headers=e,json=base).status_code==409
    assert client.delete(f'/corrections/{id}',headers=e).status_code==409
    assert client.post(f'/corrections/{id}/review',headers=a,json={'decision':'rejected','note':'Từ chối'}).status_code==409
    assert client.get('/assignments',headers=e).json()[0]['attendance']['status']=='adjusted'
    assert any(x['action']=='Duyệt điều chỉnh chấm công' for x in client.get('/audit',headers=a).json())

def test_pending_correction_full_crud_and_future_rejection(client):
    e=headers('employee');base={'assignment_id':'assignment','requested_in':'2026-10-29T07:00:00Z','reason':'Đề nghị xác nhận giờ vào thực tế'}
    assert client.post('/corrections',headers=e,json={**base,'requested_in':'2026-10-29T09:00:00Z'}).status_code==400
    r=client.post('/corrections',headers=e,json=base);assert r.status_code==201;id=r.json()['id']
    assert client.post('/corrections',headers=e,json=base).status_code==409
    assert client.put(f'/corrections/{id}',headers=e,json={**base,'reason':'Đã bổ sung lý do chi tiết hơn'}).status_code==200
    assert client.delete(f'/corrections/{id}',headers=e).status_code==200

def test_csv_and_dashboard(client):
    a=headers('admin');assert client.get('/reports/csv',headers=a).content.startswith(b'\xef\xbb\xbf')
    d=client.get('/dashboard',headers=headers('employee')).json()
    assert d['scheduled']==1 and all(x['user_id']=='employee' for x in d['assignments'])
