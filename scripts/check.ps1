$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
flutter analyze
if ($LASTEXITCODE -ne 0) { throw 'Flutter analyze failed' }
flutter test
if ($LASTEXITCODE -ne 0) { throw 'Flutter tests failed' }
node deploy/email/test_bridge.cjs
if ($LASTEXITCODE -ne 0) { throw 'Email bridge checks failed' }
Push-Location backend
try {
    & ./.venv/Scripts/python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
} finally { Pop-Location }
