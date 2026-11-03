# 배포 파일 만들기: release\KH1Korean-<버전>.zip (실행 파일 + 안내 + 라이선스)
# 사용: powershell -ExecutionPolicy Bypass -File installer\build_release.ps1
# 준비: .venv-build (pillow, pyinstaller), third_party\OpenKH.Panacea.dll, translation\src 최신 (tools\tables.py strip)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
if (-not (Test-Path "third_party\OpenKH.Panacea.dll")) { throw "third_party\OpenKH.Panacea.dll 없음 (OpenKH 릴리스에서 복사)" }
$ver = (Select-String -Path "installer\app.py" -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value
& ".venv-build\Scripts\pyinstaller.exe" "installer\kh1ko.spec" --distpath dist --workpath build\pyi --noconfirm
if ($LASTEXITCODE -ne 0) { throw "pyinstaller 실패" }
$out = "release\KH1Korean-$ver"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force "$out\licenses" | Out-Null
Copy-Item "dist\KH1Korean.exe" $out
Copy-Item "installer\README-release.txt" "$out\README.txt"
Copy-Item "third_party\LICENSE-OpenKH.txt", "third_party\NOTICE-OpenKH.txt" "$out\licenses"
$zip = "release\KH1Korean-$ver.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "$out\*" -DestinationPath $zip
Write-Output "만듦: $zip"
