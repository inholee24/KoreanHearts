# 배포 파일 만들기: release\KoreanHearts-<버전>.zip (실행 파일 + 안내 + 라이선스)
# 사용: powershell -ExecutionPolicy Bypass -File installer\build_release.ps1
# 준비: .venv-build (pillow, pyinstaller), third_party\OpenKH.Panacea.dll, <타이틀>\translation\src 최신 (kh1\tools\tables.py strip)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
if (-not (Test-Path "third_party\OpenKH.Panacea.dll")) { throw "third_party\OpenKH.Panacea.dll 없음 (OpenKH 릴리스에서 복사)" }
$ver = (Select-String -Path "installer\app.py" -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value
# 묶는 번역의 커밋. 번역·도구·설치 프로그램에 커밋 안 된 변경이 있으면 -dirty (실행 때 GitHub 최신을 받게 된다)
New-Item -ItemType Directory -Force build | Out-Null
$sha = (git rev-parse HEAD).Trim()
if (git status --porcelain -- kh1/tools kh1/translation/src recom/tools recom/translation/src installer) { $sha += "-dirty" }
Set-Content -Path "build\source.txt" -Value $sha -NoNewline -Encoding ascii
& ".venv-build\Scripts\pyinstaller.exe" "installer\koreanhearts.spec" --distpath dist --workpath build\pyi --noconfirm
if ($LASTEXITCODE -ne 0) { throw "pyinstaller 실패" }
$out = "release\KoreanHearts-$ver"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force "$out\licenses" | Out-Null
Copy-Item "dist\KoreanHearts.exe" $out
Copy-Item "installer\README-release.txt" "$out\README.txt"
Copy-Item "LICENSE" "$out\licenses\LICENSE-KoreanHearts.txt"
Copy-Item "NOTICE" "$out\licenses\NOTICE-KoreanHearts.txt"
Copy-Item "third_party\licenses\*.txt" "$out\licenses"
$zip = "release\KoreanHearts-$ver.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "$out\*" -DestinationPath $zip
Write-Output "만듦: $zip"
# 자동 업데이트(installer/selfupdate.py)가 찾는 규칙: 태그 v<버전>, 자산 이름 KoreanHearts-<버전>.zip 그대로, 정식 릴리스(초안·시험판 아님)
Write-Output "GitHub 릴리스: 태그 v$ver, 자산 KoreanHearts-$ver.zip (이름 그대로), 시험판 아님"
