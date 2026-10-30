"""Protocol/security tests; the ML engine is explicitly mocked in these tests."""
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from sqlalchemy import select, func

from app import biometric, security
from app.db import (AuthSession, BiometricChallenge, BiometricDevice,
                    BiometricSessionLink, SessionLocal, User)
from conftest import PASSWORD, headers


@pytest.fixture(autouse=True)
def biometric_clock(client, monkeypatch):
    monkeypatch.setattr(biometric, 'now', lambda: client.fixed)


def key_pair():
    private = ec.generate_private_key(ec.SECP256R1())
    public = base64.b64encode(private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
    return private, public


def proof(private, challenge, images=()):
    raw_images = [base64.b64decode(value) for value in images]
    signature = private.sign(biometric.signature_message(challenge['challenge'], raw_images), ec.ECDSA(hashes.SHA256()))
    return {'challenge_id': challenge['challenge_id'], 'signature': base64.b64encode(signature).decode(), 'images': list(images)}


def begin(client, owner='employee', kind='fingerprint', key=None):
    private, public = key or key_pair()
    authorization = headers(owner)
    response = client.post('/auth/biometric/enrollment-challenge', headers=authorization,
        json={'kind': kind, 'device_name': 'ASUS kiểm thử', 'public_key': public})
    assert response.status_code == 201, response.text
    return private, public, authorization, response.json()


def enrolled(client, owner='employee'):
    private, public, authorization, challenge = begin(client, owner)
    response = client.post('/auth/biometric/enroll', headers=authorization, json=proof(private, challenge))
    assert response.status_code == 201, response.text
    return private, response.json()['device'], authorization


def issue(client, device):
    response = client.post('/auth/biometric/challenge', json={'device_id': device['id']})
    assert response.status_code == 200, response.text
    return response.json()


def signed_headers(client, private, device):
    response = client.post('/auth/biometric/verify', json=proof(private, issue(client, device)))
    assert response.status_code == 200, response.text
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def stale_or_legacy_headers(owner, *, legacy=False):
    token = headers(owner)['Authorization'].split(' ', 1)[1]
    claims = security.decode(token, 'access')
    if legacy:
        claims.pop('auth_method', None)
        claims.pop('auth_time', None)
    else:
        claims['auth_time'] -= 601
    return {'Authorization': 'Bearer ' + security.signed(claims, 3600, 'access')}


def fake_face_engine(monkeypatch, *, available=True, enroll=None, verify=None):
    templates = [[index / 128 for index in range(128)]]
    engine = SimpleNamespace(face_ready=lambda: available,
        enroll_faces=enroll or (lambda images, steps: templates),
        verify_faces=verify or (lambda images, steps, saved: 0.85))
    monkeypatch.setattr(biometric, '_face_api', lambda: engine)
    return templates


def fake_jpegs():
    # Deliberately fake fixtures: recognition is mocked, never represented as a camera test.
    return [base64.b64encode(b'\xff\xd8' + bytes([index + 1]) * 256).decode() for index in range(4)]


def enroll_fake_face(client, monkeypatch, owner='employee'):
    templates = fake_face_engine(monkeypatch)
    private, public, authorization, challenge = begin(client, owner, 'face')
    monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=3))
    response = client.post('/auth/biometric/enroll', headers=authorization,
                           json=proof(private, challenge, fake_jpegs()))
    assert response.status_code == 201, response.text
    return private, response.json()['device'], authorization, templates


def test_password_email_otp_issues_explicit_fresh_authentication(client):
    challenge = client.post('/auth/login', json={'username': 'employee', 'password': PASSWORD}).json()
    response = client.post('/auth/verify', json={'challenge_id': challenge['challenge_id'], 'code': client.codes['employee@example.com']})
    assert response.status_code == 200
    claims = security.decode(response.json()['access_token'], 'access')
    assert claims['auth_method'] == 'password_otp' and claims['auth_time'] == int(client.fixed.timestamp())
    status = client.get('/me/security', headers={'Authorization': 'Bearer ' + response.json()['access_token']}).json()
    assert status['can_enroll_biometrics'] is True


def test_fingerprint_login_preserves_database_role_and_does_not_return_key_material(client):
    private, device, authorization = enrolled(client)
    result = client.post('/auth/biometric/verify', json=proof(private, issue(client, device)))
    assert result.status_code == 200
    assert result.json()['auth_method'] == 'fingerprint'
    assert result.json()['user']['role'] == 'employee'
    authenticated = {'Authorization': 'Bearer ' + result.json()['access_token']}
    assert client.get('/me', headers=authenticated).status_code == 200
    assert client.get('/employees', headers=authenticated).status_code == 403
    status = client.get('/me/security', headers=authenticated).json()
    assert status['can_enroll_biometrics'] is False
    assert status['auth_method'] == 'fingerprint'
    for value in [device, status['devices'][0]]:
        assert not {'public_key', 'key_fingerprint', 'face_template', 'payload'} & value.keys()
    assert client.get('/me/biometric-devices', headers=authorization).json()[0]['id'] == device['id']


def test_first_setup_requires_fresh_password_otp_not_legacy_or_old_session(client):
    _, public = key_pair()
    payload = {'kind': 'fingerprint', 'device_name': 'Test device', 'public_key': public}
    assert client.post('/auth/biometric/enrollment-challenge', json=payload).status_code == 401
    for authorization in [stale_or_legacy_headers('employee'), stale_or_legacy_headers('employee', legacy=True)]:
        assert client.get('/me', headers=authorization).status_code == 200
        assert client.get('/me/security', headers=authorization).json()['can_enroll_biometrics'] is False
        response = client.post('/auth/biometric/enrollment-challenge', headers=authorization, json=payload)
        assert response.status_code == 403 and response.json()['detail']['code'] == 'fresh_otp_required'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(BiometricDevice)) == 0


def test_biometric_session_cannot_enroll_a_second_key_without_otp(client):
    private, device, _ = enrolled(client)
    authorization = signed_headers(client, private, device)
    _, new_public = key_pair()
    assert client.post('/auth/biometric/enrollment-challenge', headers=authorization,
        json={'kind': 'fingerprint', 'device_name': 'Another', 'public_key': new_public}).status_code == 403


def test_enrollment_is_owner_bound_without_consuming_another_users_challenge(client):
    private, _, authorization, challenge = begin(client)
    request = proof(private, challenge)
    assert client.post('/auth/biometric/enroll', headers=headers('other'), json=request).status_code == 403
    assert client.post('/auth/biometric/enroll', headers=authorization, json=request).status_code == 201


def test_one_use_challenge_replay_and_wrong_signature_are_rejected(client):
    private, device, _ = enrolled(client)
    challenge = issue(client, device)
    wrong, _ = key_pair()
    assert client.post('/auth/biometric/verify', json=proof(wrong, challenge)).status_code == 401
    assert client.post('/auth/biometric/verify', json=proof(private, challenge)).status_code == 401
    challenge = issue(client, device)
    signed = proof(private, challenge)
    assert client.post('/auth/biometric/verify', json=signed).status_code == 200
    assert client.post('/auth/biometric/verify', json=signed).status_code == 401


def test_concurrent_replay_creates_exactly_one_biometric_session(client):
    private, device, _ = enrolled(client)
    signed = proof(private, issue(client, device))
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: client.post('/auth/biometric/verify', json=signed).status_code, range(2)))
    assert sorted(statuses) == [200, 401]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(BiometricSessionLink)) == 1


def test_expired_challenge_and_credential_cannot_login(client):
    private, device, _ = enrolled(client)
    challenge = issue(client, device)
    with SessionLocal() as db:
        db.get(BiometricChallenge, challenge['challenge_id']).expires_at = client.fixed - timedelta(seconds=1)
        db.commit()
    assert client.post('/auth/biometric/verify', json=proof(private, challenge)).status_code == 401
    with SessionLocal() as db:
        db.get(BiometricDevice, device['id']).expires_at = client.fixed - timedelta(seconds=1)
        db.commit()
    assert client.post('/auth/biometric/challenge', json={'device_id': device['id']}).status_code == 401


def test_revocation_is_owner_only_and_rejects_existing_biometric_sessions(client):
    private, device, owner = enrolled(client)
    authenticated = signed_headers(client, private, device)
    assert client.delete('/me/biometric-devices/' + device['id'], headers=headers('other')).status_code == 404
    response = client.delete('/me/biometric-devices/' + device['id'], headers=owner)
    assert response.status_code == 200 and response.json()['current_session_revoked'] is False
    assert client.get('/me', headers=authenticated).status_code == 401
    assert client.get('/me', headers=owner).status_code == 200
    assert client.post('/auth/biometric/challenge', json={'device_id': device['id']}).status_code == 401


def test_self_revocation_reports_that_current_biometric_session_is_closed(client):
    private, device, _ = enrolled(client)
    authorization = signed_headers(client, private, device)
    response = client.delete('/me/biometric-devices/' + device['id'], headers=authorization)
    assert response.status_code == 200 and response.json()['current_session_revoked'] is True
    assert client.get('/me', headers=authorization).status_code == 401


def test_expired_device_rejects_already_issued_access_token(client):
    private, device, _ = enrolled(client)
    authorization = signed_headers(client, private, device)
    with SessionLocal() as db:
        db.get(BiometricDevice, device['id']).expires_at = client.fixed - timedelta(seconds=1)
        db.commit()
    assert client.get('/me', headers=authorization).status_code == 401


def test_deactivating_account_revokes_device_and_future_login(client):
    private, device, _ = enrolled(client)
    signed = proof(private, issue(client, device))
    assert client.put('/employees/employee', headers=headers('admin'),
        json={'full_name': 'Employee', 'active': False, 'role': 'employee'}).status_code == 200
    assert client.post('/auth/biometric/verify', json=signed).status_code == 401
    with SessionLocal() as db:
        assert db.get(BiometricDevice, device['id']).revoked is True


def test_challenge_purpose_is_not_interchangeable(client):
    private, _, owner, challenge = begin(client)
    assert client.post('/auth/biometric/verify', json=proof(private, challenge)).status_code == 401
    assert client.post('/auth/biometric/enroll', headers=owner, json=proof(private, challenge)).status_code == 201


def test_malformed_and_wrong_curve_public_keys_are_rejected(client):
    owner = headers('employee')
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    p384 = ec.generate_private_key(ec.SECP384R1()).public_key()
    keys = ['A' * 124] + [base64.b64encode(key.public_bytes(serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo)).decode() for key in [rsa_key, p384]]
    for value in keys:
        assert client.post('/auth/biometric/enrollment-challenge', headers=owner,
            json={'kind': 'fingerprint', 'device_name': 'Bad key', 'public_key': value}).status_code == 400


def test_public_key_cannot_be_reused_by_another_account(client):
    pair = key_pair()
    private, public, authorization, challenge = begin(client, key=pair)
    assert client.post('/auth/biometric/enroll', headers=authorization, json=proof(private, challenge)).status_code == 201
    response = client.post('/auth/biometric/enrollment-challenge', headers=headers('other'),
        json={'kind': 'fingerprint', 'device_name': 'Clone', 'public_key': public})
    assert response.status_code == 409


def test_authentication_cannot_supply_role_or_raw_template(client):
    private, device, _ = enrolled(client)
    signed = proof(private, issue(client, device))
    for extra in [{'role': 'admin'}, {'auth_method': 'password_otp'}, {'template': [1, 0, 0]}]:
        response = client.post('/auth/biometric/verify', json={**signed, **extra})
        assert response.status_code == 422 and 'access_token' not in response.json()


def test_face_enrollment_fails_closed_when_engine_unavailable(client, monkeypatch):
    fake_face_engine(monkeypatch, available=False)
    _, public = key_pair()
    response = client.post('/auth/biometric/enrollment-challenge', headers=headers('employee'),
        json={'kind': 'face', 'device_name': 'ASUS face', 'public_key': public})
    assert response.status_code == 503
    assert client.get('/health').json()['face_ready'] is False
    assert client.get('/health').json()['security_version'] == '2'


def test_face_reference_is_encrypted_bound_to_account_and_never_in_responses(client, monkeypatch):
    private, device, owner, templates = enroll_fake_face(client, monkeypatch)
    with SessionLocal() as db:
        stored = db.get(BiometricDevice, device['id']).face_template
    assert isinstance(stored, str) and json.dumps(templates) not in stored
    assert biometric._decrypt_template(stored, 'employee', device['id']) == templates
    with pytest.raises(Exception) as error:
        biometric._decrypt_template(stored, 'other', device['id'])
    assert error.value.status_code == 401
    for endpoint in ['/me/security', '/me/biometric-devices']:
        response = client.get(endpoint, headers=owner)
        assert stored not in response.text and 'face_template' not in response.text and 'public_key' not in response.text
    audit = client.get('/audit', headers=headers('admin')).text
    assert stored not in audit and all(image not in audit for image in fake_jpegs())


def test_face_login_uses_registered_template_and_signed_image_hashes(client, monkeypatch):
    private, device, _, templates = enroll_fake_face(client, monkeypatch)
    captured = {}
    def recognize(images, steps, saved):
        captured.update(images=images, steps=steps, saved=saved)
        return 0.88
    fake_face_engine(monkeypatch, verify=recognize)
    challenge = issue(client, device)
    monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=6))
    signed = proof(private, challenge, fake_jpegs())
    response = client.post('/auth/biometric/verify', json=signed)
    assert response.status_code == 200 and response.json()['auth_method'] == 'face'
    assert captured['saved'] == templates and captured['steps'] == challenge['steps']
    assert len(captured['images']) == 4
    assert 'score' not in response.json() and 'template' not in response.json()
    assert client.post('/auth/biometric/verify', json=signed).status_code == 401


def test_tampered_face_bytes_fail_signature_before_recognition(client, monkeypatch):
    private, device, _, _ = enroll_fake_face(client, monkeypatch)
    calls = []
    fake_face_engine(monkeypatch, verify=lambda *args: calls.append(True))
    challenge = issue(client, device)
    monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=6))
    signed = proof(private, challenge, fake_jpegs())
    signed['images'][0] = base64.b64encode(b'\xff\xd8' + b'x' * 256).decode()
    assert client.post('/auth/biometric/verify', json=signed).status_code == 401
    assert not calls


def test_wrong_face_and_incomplete_pose_do_not_issue_session(client, monkeypatch):
    private, device, _, _ = enroll_fake_face(client, monkeypatch)
    class FaceMismatch(ValueError):
        message = 'Face does not match'
    def mismatch(*args):
        raise FaceMismatch()
    fake_face_engine(monkeypatch, verify=mismatch)
    challenge = issue(client, device)
    monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=6))
    assert client.post('/auth/biometric/verify', json=proof(private, challenge, fake_jpegs())).status_code == 401
    challenge = issue(client, device)
    assert client.post('/auth/biometric/verify', json=proof(private, challenge, fake_jpegs()[:2])).status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(BiometricSessionLink)) == 0


def test_face_revocation_removes_encrypted_reference(client, monkeypatch):
    _, device, owner, _ = enroll_fake_face(client, monkeypatch)
    assert client.delete('/me/biometric-devices/' + device['id'], headers=owner).status_code == 200
    with SessionLocal() as db:
        row = db.get(BiometricDevice, device['id'])
        assert row.revoked and row.face_template is None


@pytest.mark.parametrize('event,expected_status', [
    ('deactivate', 401), ('unverify', 401), ('revoke_session', 401),
    ('expire_session', 401), ('change_session_owner', 401), ('stale_otp', 403),
    ('expire_challenge', 400),
])
def test_face_enrollment_rechecks_authority_after_inference(client, monkeypatch, event, expected_status):
    fake_face_engine(monkeypatch)
    private, _, authorization, challenge = begin(client, kind='face')
    session_id = security.decode(authorization['Authorization'].split(' ', 1)[1], 'access')['jti']
    monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=3))

    def concurrent_change(images, steps):
        with SessionLocal() as db:
            account = db.get(User, 'employee')
            session = db.get(AuthSession, session_id)
            if event == 'deactivate':
                account.active = False
            elif event == 'unverify':
                account.verified = False
            elif event == 'revoke_session':
                session.revoked = True
            elif event == 'expire_session':
                session.expires_at = client.fixed - timedelta(seconds=1)
            elif event == 'change_session_owner':
                session.user_id = 'other'
            elif event == 'stale_otp':
                monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=601))
            elif event == 'expire_challenge':
                monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=121))
            db.commit()
        return [[index / 128 for index in range(128)]]

    fake_face_engine(monkeypatch, enroll=concurrent_change)
    response = client.post('/auth/biometric/enroll', headers=authorization,
                           json=proof(private, challenge, fake_jpegs()))
    assert response.status_code == expected_status, response.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(BiometricDevice)) == 0
        assert db.get(BiometricChallenge, challenge['challenge_id']).used is True
        # Even restoring the account later cannot resurrect the used setup proof.
        account = db.get(User, 'employee')
        account.active = account.verified = True
        session = db.get(AuthSession, session_id)
        session.revoked, session.user_id = False, 'employee'
        session.expires_at = client.fixed + timedelta(hours=1)
        db.commit()
    monkeypatch.setattr(biometric, 'now', lambda: client.fixed + timedelta(seconds=4))
    retry = client.post('/auth/biometric/enroll', headers=authorization,
                        json=proof(private, challenge, fake_jpegs()))
    assert retry.status_code == 400


def test_face_request_size_and_invalid_base64_are_rejected_without_echo(client):
    oversized = b'x' * (biometric.MAX_REQUEST_BYTES + 1)
    response = client.post('/auth/biometric/verify', content=oversized, headers={'Content-Type': 'application/json'})
    assert response.status_code == 413
    private, device, _ = enrolled(client)
    signed = proof(private, issue(client, device))
    signed['images'] = ['private-image-not-valid-base64!' * 4]
    response = client.post('/auth/biometric/verify', json=signed)
    assert response.status_code == 400 and signed['images'][0] not in response.text


def test_public_unknown_device_is_generic_and_rate_limited(client):
    id = '00000000-0000-0000-0000-000000000001'
    for _ in range(12):
        response = client.post('/auth/biometric/challenge', json={'device_id': id})
        assert response.status_code == 401 and 'username' not in response.json()
    assert client.post('/auth/biometric/challenge', json={'device_id': id}).status_code == 429
