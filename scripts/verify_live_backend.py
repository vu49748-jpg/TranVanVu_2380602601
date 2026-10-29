"""Run manually in a local terminal: python scripts/verify_live_backend.py [--csv].

Reads backend/.env.deploy without echoing credentials. A real admin login OTP
will be emailed to the owner's configured address; enter it in the hidden local
prompt, never in chat. Temporary fixtures are deleted in reverse dependency
order. Audit entries and the real login email remain. No POST is retried.
"""
import argparse
import getpass
import ipaddress
import json
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = 'https://tranvanvu-2380602601-api.onrender.com'
PROJECT = 'TranVanVu_2380602601'


class SmokeError(Exception):
    pass


def read_config(path):
    values = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, sep, value = line.partition('=')
        if sep and re.fullmatch(r'[A-Z_][A-Z_0-9]*', name.strip()):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[name.strip()] = value
    return values


def public_url(value):
    parsed = urllib.parse.urlsplit(value.strip())
    host = (parsed.hostname or '').lower()
    if (parsed.scheme != 'https' or not host or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ('', '/')
            or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal'))):
        raise SmokeError('API_BASE_URL must be a public HTTPS origin.')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if '.' not in host or re.fullmatch(r'[0-9.]+', host):
            raise SmokeError('API_BASE_URL must use a public hostname.')
    else:
        if not address.is_global:
            raise SmokeError('Private/local API addresses are forbidden.')
    return value.strip().rstrip('/')


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, url, report):
        self.url, self.report, self.token = url, report, None
        self.opener = urllib.request.build_opener(NoRedirects())

    def request(self, method, path, body=None, *, authenticated=True, expected=200, raw=False):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if authenticated and self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        request = urllib.request.Request(self.url + path, method=method, headers=headers,
            data=json.dumps(body).encode() if body is not None else None)
        try:
            response = self.opener.open(request, timeout=90)
        except urllib.error.HTTPError as error:
            response = error
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SmokeError('Network request failed; the request was not retried.') from None
        with response:
            status, data = response.code, response.read()
        expected_codes = (expected,) if isinstance(expected, int) else expected
        if status not in expected_codes:
            raise SmokeError(f'{method} {path}: unexpected HTTP {status}.')
        if raw:
            return data
        try:
            return json.loads(data)
        except (ValueError, UnicodeDecodeError):
            raise SmokeError(f'{method} {path}: invalid JSON response.') from None


def require(condition, message):
    if not condition:
        raise SmokeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', action='store_true', help='Also fetch CSV into memory; never save its contents.')
    args = parser.parse_args()
    report = {'project': PROJECT, 'started_at': datetime.now(timezone.utc).isoformat(),
        'passed': False, 'checks': [], 'cleanup': [], 'uncertain_creates': []}
    fixtures, client = [], None
    tag = 'smoke_' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '_' + secrets.token_hex(4)
    report['fixture_tag'] = tag

    def mark(name):
        report['checks'].append({'name': name, 'passed': True})

    def create(resource, body):
        try:
            row = client.request('POST', '/' + resource, body, expected=201)
            require(isinstance(row, dict) and isinstance(row.get('id'), str), 'Creation response has no ID.')
            require(re.fullmatch(r'[0-9a-f-]{36}', row['id']), 'Creation returned an unsafe ID.')
            require(all(row.get(key) == value for key, value in body.items() if key != 'password'),
                'Creation response does not match this run\'s owned fixture.')
            require(resource != 'employees' or row.get('role') == 'employee', 'Temporary user must never be admin.')
        except (Exception, KeyboardInterrupt):
            report['uncertain_creates'].append({'resource': resource, 'fixture_tag': tag})
            raise
        fixtures.append((resource, row['id']))
        mark('create_' + resource)
        return row['id']

    def read_and_update(resource, row_id, body, field, expected_value):
        rows = client.request('GET', '/' + resource)
        require(any(row.get('id') == row_id for row in rows), 'Created fixture missing from list.')
        mark('read_' + resource)
        row = client.request('PUT', f'/{resource}/{row_id}', body)
        require(row.get('id') == row_id and row.get(field) == expected_value, 'Update verification failed.')
        mark('update_' + resource)

    try:
        config = read_config(ROOT / 'backend' / '.env.deploy')
        require(bool(config.get('ADMIN_PASSWORD')), 'ADMIN_PASSWORD is missing from local configuration.')
        client = Client(public_url(config.get('API_BASE_URL') or DEFAULT_URL), report)
        report['api_url'] = client.url
        health = client.request('GET', '/health', authenticated=False)
        require(health.get('project') == PROJECT and health.get('status') == 'ok', 'Wrong project or unhealthy backend.')
        require(health.get('email_configured') is True, 'Backend email configuration is incomplete.')
        mark('public_health_and_project')
        for path in ('/me', '/employees'):
            client.request('GET', path, authenticated=False, expected=401)
        mark('unauthorized_routes_return_401')
        require(sys.stdin.isatty(), 'Run this script in an interactive local terminal for the hidden OTP prompt.')
        print('An admin OTP will be sent to your configured email. Enter it only in this terminal.')
        challenge = client.request('POST', '/auth/login', {'username': config.get('ADMIN_USERNAME') or 'tranvanvu',
            'password': config['ADMIN_PASSWORD']}, authenticated=False)
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            code = getpass.getpass('Admin email OTP (hidden): ').strip()
        require(re.fullmatch(r'\d{6}', code), 'OTP must contain exactly six digits.')
        result = client.request('POST', '/auth/verify', {'challenge_id': challenge['challenge_id'], 'code': code}, authenticated=False)
        code = None
        client.token = result.get('access_token')
        require(isinstance(client.token, str) and client.token, 'OTP verification returned no session.')
        require(client.request('GET', '/me').get('role') == 'admin', 'Authenticated account is not admin.')
        mark('real_email_otp_and_admin_role')
        site = {'name': tag + '_site', 'address': 'Temporary smoke test', 'latitude': 10.8, 'longitude': 106.7, 'radius_m': 150}
        site_id = create('sites', site)
        read_and_update('sites', site_id, {**site, 'radius_m': 175}, 'radius_m', 175)
        shift = {'name': tag + '_shift', 'site_id': site_id, 'start_time': '08:00', 'end_time': '12:00', 'grace_minutes': 10}
        shift_id = create('shifts', shift)
        read_and_update('shifts', shift_id, {**shift, 'grace_minutes': 15}, 'grace_minutes', 15)
        employee_id = create('employees', {'username': tag, 'email': tag + '@example.com',
            'full_name': tag + '_employee', 'password': secrets.token_urlsafe(24)})
        read_and_update('employees', employee_id, {'full_name': tag + '_updated', 'department': 'Temporary smoke test',
            'phone': '', 'role': 'employee', 'active': True}, 'full_name', tag + '_updated')
        tomorrow = (datetime.now(timezone(timedelta(hours=7))).date() + timedelta(days=1))
        assignment = {'user_id': employee_id, 'shift_id': shift_id, 'work_date': tomorrow.isoformat()}
        assignment_id = create('assignments', assignment)
        next_date = (tomorrow + timedelta(days=1)).isoformat()
        read_and_update('assignments', assignment_id, {**assignment, 'work_date': next_date}, 'work_date', next_date)
        if args.csv:
            require(client.request('GET', '/reports/csv', raw=True).startswith(b'\xef\xbb\xbf'), 'CSV UTF-8 BOM is missing.')
            mark('csv_export')
        report['passed'] = True
    except (Exception, KeyboardInterrupt) as error:
        report['error'] = str(error) if isinstance(error, SmokeError) else 'Stopped: ' + type(error).__name__
    finally:
        for resource, row_id in reversed(fixtures):
            entry = {'resource': resource, 'id': row_id, 'deleted': False}
            try:
                client.request('DELETE', f'/{resource}/{row_id}', expected=(200, 404))
                rows = client.request('GET', '/' + resource)
                entry['deleted'] = not any(row.get('id') == row_id for row in rows)
            except (Exception, KeyboardInterrupt) as error:
                entry['error'] = str(error) if isinstance(error, SmokeError) else type(error).__name__
            report['cleanup'].append(entry)
        if client and client.token:
            try:
                client.request('POST', '/auth/logout')
                report['session_revoked'] = True
            except (Exception, KeyboardInterrupt):
                report['session_revoked'] = False
            client.token = None
        report['passed'] &= (all(row['deleted'] for row in report['cleanup'])
            and not report['uncertain_creates'] and report.get('session_revoked', True))
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        target = ROOT / 'artifacts' / 'live_api_report.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS' if report['passed'] else 'INCOMPLETE/FAILED', '— sanitized report:', target)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
