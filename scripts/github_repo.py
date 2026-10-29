"""Use existing Windows Git credentials without printing or saving the token.
Read-only by default; --create creates a PRIVATE repository for this project.
"""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

def main():
    credential = subprocess.run(['git','credential','fill'], input='protocol=https\nhost=github.com\n\n',
        text=True, capture_output=True, env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}, timeout=30)
    values = dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
    token = values.get('password')
    if not token: raise SystemExit('GitHub credential unavailable; sign in with Git Credential Manager first.')
    def api(path, data=None):
        request = urllib.request.Request('https://api.github.com'+path,
            headers={'Authorization':'Bearer '+token, 'Accept':'application/vnd.github+json',
                'X-GitHub-Api-Version':'2022-11-28','User-Agent':'TranVanVu-2380602601'},
            data=json.dumps(data).encode() if data is not None else None)
        with urllib.request.urlopen(request,timeout=30) as response: return json.load(response)
    account=api('/user'); name='TranVanVu_2380602601'
    print(json.dumps({'github_login':account['login'],'id':account['id']},ensure_ascii=False))
    try: repo=api(f'/repos/{account["login"]}/{name}')
    except urllib.error.HTTPError as error:
        if error.code!=404: raise SystemExit(f'GitHub request failed: HTTP {error.code}')
        if '--create' not in sys.argv:
            print('Repository does not exist.');return
        repo=api('/user/repos', {'name':name,'private':True,'description':'Flutter Android • Chấm công nhân viên • Trần Văn Vũ 2380602601 • Nhóm 7','auto_init':False})
    print(json.dumps({k:repo[k] for k in ['html_url','clone_url','private','size']},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except urllib.error.HTTPError as error:raise SystemExit(f'GitHub request failed: HTTP {error.code}')
