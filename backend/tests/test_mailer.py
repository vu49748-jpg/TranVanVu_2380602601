import hashlib
import hmac
import pytest
from app import mailer
from app.mailer import send_otp as actual_send_otp

def test_apps_script_hmac_contract_and_no_secret_in_body(monkeypatch):
    monkeypatch.setattr(mailer, 'EMAIL_TRANSPORT', 'apps_script')
    monkeypatch.setenv('GAS_WEBHOOK_URL', 'https://script.google.com/macros/s/test/exec')
    secret = 'test-only-shared-key-must-never-go-to-client'
    monkeypatch.setenv('GAS_SHARED_SECRET', secret)
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'ok':True}
    def post(url, **kwargs):
        captured.update(kwargs); return Response()
    monkeypatch.setattr(mailer.httpx, 'post', post)
    actual_send_otp('staff@example.com', '123456')
    payload = captured['json']
    expected = hmac.new(secret.encode(), '|'.join([payload['email'],payload['code'],payload['timestamp'],payload['nonce']]).encode(), hashlib.sha256).hexdigest()
    assert payload['signature'] == expected
    assert secret not in str(payload)
    assert captured['follow_redirects'] is True

def test_apps_script_negative_response_is_not_success(monkeypatch):
    monkeypatch.setattr(mailer, 'EMAIL_TRANSPORT', 'apps_script')
    monkeypatch.setenv('GAS_WEBHOOK_URL', 'https://script.google.com/macros/s/test/exec')
    monkeypatch.setenv('GAS_SHARED_SECRET', 'test-key-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'ok':False}
    monkeypatch.setattr(mailer.httpx, 'post', lambda *a,**k:Response())
    with pytest.raises(RuntimeError): actual_send_otp('staff@example.com','123456')
