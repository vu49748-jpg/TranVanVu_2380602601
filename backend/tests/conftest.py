import os
import tempfile
import pytest

test_dir = tempfile.TemporaryDirectory(prefix='tranvanvu_test_')
os.environ['APP_ENV'] = 'test'
os.environ['SECRET_KEY'] = 'unit-tests-only-key-never-for-production-2380602601'
os.environ['DATABASE_URL'] = f'sqlite:///{test_dir.name}/test.db'
os.environ.pop('ADMIN_EMAIL', None)
os.environ.pop('ADMIN_PASSWORD', None)

from fastapi.testclient import TestClient
from app.main import app
from app import main, security, mailer
from app.db import Base, engine, SessionLocal, User, Site, Shift, Assignment, now
from datetime import datetime, timezone, timedelta

PASSWORD = 'TestPassword2380602601!'
PASSWORD_HASH = security.passwords.hash(PASSWORD)

@pytest.fixture
def client(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    fixed = datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
    fixed = FrozenDatetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)
    import jwt.api_jwt
    monkeypatch.setattr(jwt.api_jwt, 'datetime', FrozenDatetime)
    monkeypatch.setattr(main, 'now', lambda: fixed)
    monkeypatch.setattr(security, 'now', lambda: fixed)
    codes = {}
    monkeypatch.setattr(mailer, 'send_otp', lambda email, code: codes.update({email:code}))
    with SessionLocal() as db:
        for id, role in [('admin','admin'),('employee','employee'),('other','employee')]:
            db.add(User(id=id, username=id, email=f'{id}@example.com', full_name=id,
                password_hash=PASSWORD_HASH, role=role, verified=True))
        db.add(Site(id='site', name='Văn phòng', latitude=10.8, longitude=106.7, radius_m=150))
        db.commit()
        db.add(Shift(id='shift', name='Ca chiều', site_id='site', start_time='14:00', end_time='23:00', grace_minutes=10))
        db.commit()
        db.add(Assignment(id='assignment', user_id='employee', shift_id='shift', work_date='2026-10-29'))
        db.commit()
    with TestClient(app) as c:
        c.codes = codes
        c.fixed = fixed
        yield c

@pytest.fixture(scope='session', autouse=True)
def close_test_database():
    yield
    engine.dispose()
    test_dir.cleanup()

def headers(id):
    with SessionLocal() as db:
        token = security.create_session(db, db.get(User, id))
    return {'Authorization': f'Bearer {token}'}

def evidence(client, admin_headers):
    qr = client.get('/sites/site/qr', headers=admin_headers).json()['token']
    return {'assignment_id':'assignment', 'action':'in', 'latitude':10.8, 'longitude':106.7,
        'accuracy_m':12.0, 'is_mocked':False, 'captured_at':client.fixed.isoformat(),
        'motion_rms':0.8, 'motion_samples':50, 'motion_duration_ms':3000, 'qr_token':qr}
