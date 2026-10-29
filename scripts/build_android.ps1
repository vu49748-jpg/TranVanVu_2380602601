param([string]$ApiBaseUrl = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if ($ApiBaseUrl -ne '' -and -not $ApiBaseUrl.StartsWith('https://')) {
    throw 'API_BASE_URL must be the public HTTPS backend URL.'
}
$buildArgs = @('build', 'apk', '--release')
if ($ApiBaseUrl -ne '') { $buildArgs += "--dart-define=API_BASE_URL=$ApiBaseUrl" }
& flutter @buildArgs
if ($LASTEXITCODE -ne 0) { throw 'Android APK build failed' }
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
Copy-Item -LiteralPath build/app/outputs/flutter-apk/app-release.apk -Destination artifacts/TranVanVu_2380602601.apk -Force
Write-Output 'APK: artifacts/TranVanVu_2380602601.apk'
