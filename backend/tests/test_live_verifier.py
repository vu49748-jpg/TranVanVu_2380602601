"""Offline verification of fixture ownership, cleanup and secret sanitization."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID


SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'verify_live_backend.py'
spec = importlib.util.spec_from_file_location('live_verifier_offline', SCRIPT)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

PASSWORD = 'OFFLINE-password-that-must-not-appear-in-reports'
OTP = '726491'
TOKEN = 'OFFLINE-JWT-that-must-not-appear-in-reports'


class MemoryApi:
    """A stateful API double with foreign-key deletion constraints."""

    def __init__(self, uncertain_resource=None):
        self.token = None
        self.revoked = False
        self.calls = []
        self.created = []
        self.uncertain_resource = uncertain_resource
        self.rows = {resource: {} for resource in ('sites', 'shifts', 'employees', 'assignments')}
        for index, resource in enumerate(self.rows, 101):
            row_id = str(UUID(int=index))
            self.rows[resource][row_id] = {'id': row_id, 'name': 'Existing user-owned record'}
        self.original = copy.deepcopy(self.rows)

    def request(self, method, path, body=None, *, authenticated=True, expected=200, raw=False):
        self.calls.append((method, path))
        if path == '/health':
            return {'project': verifier.PROJECT, 'status': 'ok', 'email_configured': True}
        if not authenticated and path in ('/me', '/employees'):
            assert expected == 401
            return {'detail': 'Vui lòng đăng nhập.'}
        if path == '/auth/login':
            assert body == {'username': 'tranvanvu', 'password': PASSWORD}
            return {'challenge_id': 'offline-challenge'}
        if path == '/auth/verify':
            assert body == {'challenge_id': 'offline-challenge', 'code': OTP}
            return {'access_token': TOKEN}
        assert authenticated and self.token == TOKEN
        if path == '/me':
            return {'id': str(UUID(int=103)), 'role': 'admin'}
        if path == '/auth/logout':
            self.revoked = True
            return {'message': 'Đã đăng xuất.'}
        if path == '/reports/csv':
            assert raw
            return b'\xef\xbb\xbfheader\r\n'
        parts = path.strip('/').split('/')
        resource = parts[0]
        assert resource in self.rows, 'Unexpected route; no network fallback is allowed.'
        if method == 'GET':
            assert len(parts) == 1
            return copy.deepcopy(list(self.rows[resource].values()))
        if method == 'POST':
            assert len(parts) == 1
            row_id = str(UUID(int=201 + len(self.created)))
            row = {key: value for key, value in body.items() if key != 'password'}
            row['id'] = row_id
            if resource == 'employees':
                row['role'] = 'employee'
            self.rows[resource][row_id] = row
            self.created.append((resource, row_id))
            if resource == self.uncertain_resource:
                # The server committed, but the client never learned this UUID.
                raise verifier.SmokeError('Create response was lost; request was not retried.')
            return copy.deepcopy(row)
        assert len(parts) == 2, 'Never allow broad deletion of a collection.'
        row_id = parts[1]
        assert row_id not in self.original[resource], 'Existing data must never be modified.'
        if method == 'PUT':
            self.rows[resource][row_id].update(body)
            return copy.deepcopy(self.rows[resource][row_id])
        assert method == 'DELETE'
        dependencies = {'sites': ('shifts', 'site_id'), 'shifts': ('assignments', 'shift_id'),
            'employees': ('assignments', 'user_id')}
        if resource in dependencies:
            child, field = dependencies[resource]
            if any(row.get(field) == row_id for row in self.rows[child].values()):
                raise verifier.SmokeError('HTTP 409: dependent temporary row still exists.')
        del self.rows[resource][row_id]
        return {'message': 'Deleted temporary fixture.'}


def run_offline(monkeypatch, tmp_path, api, *, csv=False):
    monkeypatch.setattr(verifier, 'ROOT', tmp_path)

    def fake_config(path):
        assert path == tmp_path / 'backend' / '.env.deploy'
        return {'ADMIN_USERNAME': 'tranvanvu', 'ADMIN_PASSWORD': PASSWORD,
            'API_BASE_URL': verifier.DEFAULT_URL}

    monkeypatch.setattr(verifier, 'read_config', fake_config)
    monkeypatch.setattr(verifier, 'Client', lambda url, report: api)
    monkeypatch.setattr(verifier.sys, 'stdin', SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(verifier.sys, 'argv', ['verify_live_backend.py'] + (['--csv'] if csv else []))
    monkeypatch.setattr(verifier.getpass, 'getpass', lambda prompt: OTP)
    # The report may contain the verified public origin, but never credentials.
    api.url = verifier.DEFAULT_URL
    exit_code = verifier.main()
    raw_report = (tmp_path / 'artifacts' / 'live_api_report.json').read_text(encoding='utf-8')
    return exit_code, json.loads(raw_report), raw_report


def assert_sanitized(raw_report, terminal_output):
    for secret in (PASSWORD, OTP, TOKEN):
        assert secret not in raw_report
        assert secret not in terminal_output


def test_success_cleans_only_owned_fixtures_in_dependency_order(monkeypatch, tmp_path, capsys):
    api = MemoryApi()
    exit_code, report, raw = run_offline(monkeypatch, tmp_path, api, csv=True)
    assert exit_code == 0 and report['passed'] is True
    assert len(api.created) == 4
    deletes = [path for method, path in api.calls if method == 'DELETE']
    expected = [f'/{resource}/{row_id}' for resource, row_id in reversed(api.created)]
    assert deletes == expected
    assert api.rows == api.original, 'All original rows survive; all acknowledged fixtures are gone.'
    assert [(row['resource'], row['id']) for row in report['cleanup']] == list(reversed(api.created))
    assert all(row['deleted'] for row in report['cleanup'])
    assert report['uncertain_creates'] == []
    assert api.revoked and api.token is None and report['session_revoked'] is True
    assert ('GET', '/reports/csv') in api.calls
    output = capsys.readouterr()
    assert_sanitized(raw, output.out + output.err)


def test_lost_post_response_cleans_known_ids_without_guessing_unknown_id(monkeypatch, tmp_path, capsys):
    api = MemoryApi(uncertain_resource='employees')
    exit_code, report, raw = run_offline(monkeypatch, tmp_path, api)
    assert exit_code == 1 and report['passed'] is False
    assert len(api.created) == 3
    known, unknown = api.created[:2], api.created[2]
    deletes = [path for method, path in api.calls if method == 'DELETE']
    assert deletes == [f'/{resource}/{row_id}' for resource, row_id in reversed(known)]
    assert f'/{unknown[0]}/{unknown[1]}' not in deletes
    assert api.calls.count(('POST', '/employees')) == 1, 'An ambiguous POST must never be retried.'
    assert ('POST', '/assignments') not in api.calls
    assert report['uncertain_creates'] == [{'resource': 'employees', 'fixture_tag': report['fixture_tag']}]
    assert all(row['deleted'] for row in report['cleanup'])
    for resource, original in api.original.items():
        assert all(api.rows[resource][row_id] == row for row_id, row in original.items())
    assert set(api.rows['employees']) - set(api.original['employees']) == {unknown[1]}
    assert all(set(api.rows[resource]) == set(api.original[resource]) for resource in ('sites', 'shifts', 'assignments'))
    assert api.revoked and api.token is None and report['session_revoked'] is True
    output = capsys.readouterr()
    assert_sanitized(raw, output.out + output.err)
