# KoreanHearts: 킹덤 하츠 한글화 프로젝트

**KINGDOM HEARTS FINAL MIX** (PC Steam 판 *KINGDOM HEARTS -HD 1.5+2.5 ReMIX-*)를 한국어로 플레이할 수 있게 만드는 비공식 한글화 프로젝트입니다.

이 게임은 한국어를 지원하지 않습니다. 한글 글꼴도 없고, 텍스트 엔진은 영어와 일본어를 전제로 만들어졌습니다. 그래서 문장을 옮기는 일보다 **한국어를 표시할 수 없는 엔진에서 한국어를 표시하게 하는 일**이 먼저였습니다. 이 저장소에는 번역과 함께 그 과정에서 만든 분석 자료, 변환 도구, 검증 도구, 설치 프로그램이 들어 있습니다.

| 항목 | 내용 |
|---|---|
| 대상 | KH1 FINAL MIX, PC Steam 판 (게임 언어: 영어) |
| 기간 | 2026년 6월 ~ 11월 |
| 번역 | 대사·메뉴·아이템·도움말 약 7,800줄 (게임 내 메시지 약 75만 개에 반영) |
| 글꼴 | 대화창 글꼴 1,070자, 시스템(UI) 글꼴 928자를 새로 그려 넣음 |
| 그림 속 글자 | 타이틀·전투 명령·메뉴·구미 미션 등 그림 67장 |
| 배포 | 단일 실행 파일. 원본 게임 데이터를 포함하지 않음 |
| 언어·도구 | Python (Pillow, capstone, pefile), PyInstaller, Win32 API |

---

## 1. 이 프로젝트가 어려웠던 이유

**글자를 넣을 자리가 없었습니다.**
영어판 대화창 글꼴은 알파벳과 기호를 합쳐 수백 칸짜리 텍스처 하나입니다. 한국어 번역에는 서로 다른 글자가 1,000자 넘게 필요했습니다.

**문자 코드 체계가 없었습니다.**
영어판 메시지는 1바이트 코드만 씁니다. 그 이상의 글자를 어떻게 부르는지, 즉 2바이트 코드의 존재와 해석 규칙은 문서화되어 있지 않았습니다.

**글꼴이 하나가 아니었습니다.**
대화창, 메뉴(UI), 그림 속 글자, 설정 메뉴는 서로 다른 글꼴과 다른 렌더링 경로를 씁니다. 각각을 따로 찾고 따로 해결해야 했습니다.

**엔진이 정한 값이 실행 파일 안에 있었습니다.**
글꼴 텍스처의 격자, 줄 높이, 글자 표의 최대 크기는 데이터 파일이 아니라 실행 파일에 고정되어 있었습니다. 실행 파일은 수정하지 않는 것이 원칙이라 다른 방법이 필요했습니다.

**배포 방식에도 제약이 있었습니다.**
게임 원본 데이터는 저작물이라 그대로 배포할 수 없습니다. 영어 원문이 들어 있는 메시지 파일도 마찬가지입니다.

## 2. 진행 방법

### 가설 하나, 실험 하나, 기록 하나

초기 두 달은 같은 문제를 기록 없이 여러 방향으로 시도하다 막혔습니다. 이후에는 방식을 바꿨습니다.

1. 화면에 나타날 결과를 경우별로 미리 표로 적습니다. (예: "A가 보이면 가설 확정, B가 보이면 기각")
2. 한 번에 변수 하나만 바꿔 게임에서 확인합니다.
3. 성공과 실패를 모두 [docs/work-history.md](docs/work-history.md)에 남깁니다. 기각한 가설은 "재시도하지 말 것"에 따로 모읍니다.

이 방식으로 게임 내 실험을 55차까지 진행했습니다. 9차 실험에서는 3~8차의 "글자가 안 보인다"는 결과가 코드 경로 문제가 아니라 **글자 색 문제**였다는 것이 드러났습니다. 그래서 앞선 결론을 무효로 하고 다시 쌓았습니다. 이런 판단 과정도 모두 기록에 남아 있습니다.

### 실행 파일 분석 (정적 + 동적)

데이터만으로 설명되지 않는 동작은 게임 실행 파일을 디스어셈블해 확인했습니다.

- **분석 도구를 직접 만들었습니다.** 함수 15,808개, 호출·참조·포인터 표를 색인하는 도구([tools/re/](tools/re/))를 만들었습니다. 알아낸 함수와 변수의 의미는 지식 베이스([tools/re/names.tsv](tools/re/names.tsv))에 쌓았습니다.
- **실행 중인 게임의 메모리를 확인했습니다.** 창 크기, 글꼴 표, 텍스처 크기를 읽어 정적 분석의 추론을 검증했습니다.
- **분석으로 찾은 것:**
  - 메시지 2바이트 코드 규칙: `((b0<<8)|b1) - 0x1820`
  - 디코더 버그: 특정 첫 바이트가 공백으로 처리되는 문제
  - 선택지 창 폭의 실제 출처: 이벤트 스크립트 명령의 즉값
  - 시스템 글꼴 표의 버퍼 구조

결과는 [docs/exe-analysis.md](docs/exe-analysis.md)와 [docs/file-formats.md](docs/file-formats.md)에 정리했습니다. 문서 전체에서 `확정`(디스어셈블이나 실측으로 확인)과 `추론`을 구분해 적었습니다.

### 글자 용량 문제의 해결

- **대화창 글꼴:** 일본어판이 같은 실행 파일 안에서 더 촘촘한 글꼴 배치(1,764칸)를 쓴다는 것을 찾았습니다. 그래서 영어 경로에서도 일본어판 배치를 쓰게 했습니다.
  - 한글 글리프는 맑은 고딕으로 렌더링합니다.
  - 원본과 같은 테두리와 알파 계조를 넣습니다.
  - 게임의 축소 렌더링에서 획 굵기가 고르게 보이도록 미리 보정합니다.
- **시스템 글꼴:** 텍스처를 2048로 확장했습니다. 글꼴 표를 원래 레코드 수의 약 2배(2,016개)로 늘려 게임 메모리에 연결합니다.
- **실행 파일 원본은 바꾸지 않습니다.** 필요한 값 8개는 게임 실행 중에 메모리에 씁니다. 게임이 값을 다시 초기화하면 다시 씁니다.

### 번역과 용어

- **용어 기준:** 고유명사는 시리즈 한국어 정발작(KH3)의 표기를 따릅니다. 예: 도날드, 홀로우 바스티온, 킹덤 체인. 용어집은 [docs/terminology.md](docs/terminology.md), 번역 원칙은 [docs/translation-rules.md](docs/translation-rules.md)입니다.
- **엔진 제약을 번역 규칙으로:**
  - 선택지는 줄 수를 유지합니다.
  - 아이템 이름이 들어가는 자리 뒤에는 받침에 따라 바뀌는 조사를 붙이지 않습니다.
  - 고정 크기 말풍선은 원문 용량을 넘지 않게 줄을 나눕니다.
  - 가운데 정렬 자막은 번역문 폭에 맞춰 위치를 다시 계산합니다.
- **화자와 장면:** 캐릭터별 말투, 같은 대사가 여러 월드 파일에 반복되는 경우, 퍼즐 풀이에 영어 알파벳이 필요한 장면 등을 장면 단위로 판단했습니다.
- **번역 방식:** 초안은 AI(Claude)로 작성했습니다. 용어집, 일괄 검사 도구([tools/tr_batch.py](tools/tr_batch.py)), 빌드 검증으로 일관성을 관리합니다.

### 검증 자동화

사람이 모든 장면을 플레이해 확인할 수 없는 부분은 도구로 확인합니다.

- [tools/verify_build.py](tools/verify_build.py)
  - 빌드한 메시지 파일 2,000여 개를 원본과 하나씩 대조합니다.
  - 바뀐 메시지가 모두 번역이 있는 원문이고, 글자 표로 해독했을 때 번역문과 정확히 같은지 확인합니다.
  - 확인 대상은 메시지 약 75만 개입니다.
- [tools/fixwin_check.py](tools/fixwin_check.py): 이벤트 스크립트에서 고정 크기 창 894개를 찾습니다. 번역문이 창 용량을 넘는지 검사합니다.
- [tools/sysfont_sim.py](tools/sysfont_sim.py): 실행 파일의 규칙대로 UI 글꼴을 그려 봅니다. 게임을 켜지 않고 결과를 미리 확인할 수 있습니다.

## 3. 배포 설계: 원본 데이터 없는 패치

배포 파일과 이 저장소에는 **게임 원본 파일도, 영어 원문도 들어 있지 않습니다.**

- **번역 표는 `키 + 한국어`만 저장합니다.** 영어 원문은 설치할 때 사용자 PC의 게임에서 다시 채웁니다([tools/tables.py](tools/tables.py)).
- **설치 프로그램이 한글 파일을 사용자 PC에서 직접 만듭니다.**
  - 게임 패키지(.hed/.pkg)에서 필요한 파일 2,281개만 꺼냅니다([tools/pkgextract.py](tools/pkgextract.py), OpenKH 형식 처리를 Python으로 옮김).
  - 빌드와 검증을 거친 뒤, 꺼낸 원본은 지웁니다.
  - 게임 원본 파일은 수정하지 않습니다. 결과물은 OpenKH Panacea를 통해 읽힙니다.
- **사용자가 하는 일은 실행 파일 하나를 실행하고 버튼 두 개를 누르는 것뿐입니다.** ("한글 패치 설치" → "게임 실행")
- **재현성을 확인했습니다.** 빈 저장소에서 처음부터 빌드한 결과, 그리고 배포용 실행 파일로 설치한 결과가 개발 중 게임에서 검증한 결과물 2,266개와 바이트 단위로 같습니다.

```text
사용자 PC
  게임 패키지 ──pkgextract──▶ 필요한 원본 (임시)
                                 │
  번역 표 (키+한국어) ──tables──▶ 전체 번역 표
                                 │
                    build_ko / imgtext / settingmenu / evdl_patch
                                 │
                         verify_build (문제 0 이어야 설치 진행)
                                 │
                    한글 파일 (KH1Korean/mod) ◀── Panacea 가 게임에 공급
                                       + 실행 중 메모리 패치 (글꼴 배치·표 확장)
```

## 4. 결과

- 전 월드의 대사, 이벤트 자막, 상점·합성·콜로세움 메시지, 메뉴, 아이템·어빌리티 설명, 지미니 메모, 구미 차고, 설정 메뉴, 장소 이름을 한국어로 표시합니다.
- 타이틀 화면, 전투 명령 메뉴, 메인 메뉴, 월드 제목, 구미 미션 화면 등 그림 속 글자 67장을 한글로 바꿨습니다.
- 게임 내 확인 장면 예:
  - 타이틀
  - 대사 창, 선택지
  - 전투 명령 메뉴, 일시 정지
  - 메뉴 이름·설명
  - 구미 차고 도움말
  - 설정 메뉴
  - 장소 이름
  - 확장 표의 글자(황, 흩 등)

## 5. 저장소 구조

| 경로 | 내용 |
|---|---|
| [translation/src/](translation/src/) | 번역 표 (키와 한국어만). 번역의 원본 |
| [tools/](tools/) | 추출·변환·빌드·검증 도구 |
| [tools/re/](tools/re/) | 실행 파일 분석 도구, 실행 중 메모리 패치 (`mem.py`) |
| [installer/](installer/) | 설치·실행 프로그램 (`app.py`, tkinter), PyInstaller 설정, 배포 빌드 스크립트 |
| [docs/](docs/) | 파일 형식, 실행 파일 분석, 작업 기록, 용어집, 알려진 문제 |
| [third_party/](third_party/) | OpenKH 라이선스 (`OpenKH.Panacea.dll`은 OpenKH 릴리스에서 복사) |

저장소에 넣지 않는 것(`.gitignore`): `data/`(꺼낸 원본), `mod/`(결과물), `translation/*.tsv`(원문이 들어간 전체 표), `translation/build/`, 게임 화면 캡처.

### 주요 문서

- [docs/work-history.md](docs/work-history.md): 1~55차 실험의 가설, 변경, 결과, 판단 근거
- [docs/exe-analysis.md](docs/exe-analysis.md): 실행 파일 분석 결과(함수 주소, 구조체, 분석 도구 사용법)
- [docs/file-formats.md](docs/file-formats.md): 메시지 인코딩, 글꼴 표, 텍스처 배치, 패키지 형식
- [docs/build-process.md](docs/build-process.md): 추출, 빌드, 적용, 검증 절차
- [docs/known-issues.md](docs/known-issues.md): 해결한 문제와 남은 확인 항목

## 6. 사용 방법

### 설치 (사용자)

배포 zip의 `KH1Korean.exe`를 실행하고 "한글 패치 설치" → "게임 실행"을 누릅니다. 게임하는 동안 이 창은 열어 둡니다. 자세한 내용은 [installer/README-release.txt](installer/README-release.txt)에 있습니다.

### 개발

Python 3.13 + Pillow가 필요하고, 맑은 고딕(`C:\Windows\Fonts\malgun*.ttf`)이 있어야 합니다.

```text
1. python tools/pkgextract.py "<게임 폴더>" .     필요한 원본만 data/kh1, data/settingmenu 로 (약 2.2GB)
2. python tools/tables.py expand                   translation/src + 원본 -> 전체 표 translation/*.tsv
3. (번역 작업: translation/*.tsv 의 ko 열, tools/tr_batch.py)
4. python tools/build_ko.py --layout jp --apply    대사·메뉴·글꼴 -> mod/kh1
   python tools/imgtext.py --apply                  그림 속 글자
   python tools/settingmenu.py --apply              설정 메뉴
   python tools/evdl_patch.py --apply               상점 선택지 창 폭
5. python tools/verify_build.py                     '문제 0' 이어야 함
   python tools/fixwin_check.py                     고정 크기 말풍선 넘침 'n 0'
6. python tools/tables.py strip                     커밋 전에 translation/src 갱신
   python tools/tables.py check                     strip -> expand 가 전체 표와 같은지
```

- **게임에서 확인하려면:** Panacea의 `panacea_settings.txt`에서 `mod_path`를 이 저장소의 `mod`로 둡니다. 그다음 `python tools/re/mem.py tex2x 14400 jp`를 켠 채 게임을 실행합니다.
- **배포 파일 만들기:** `powershell -ExecutionPolicy Bypass -File installer/build_release.ps1`을 실행하면 `release/KH1Korean-<버전>.zip`이 나옵니다.

## 7. 한계와 남은 일

- Steam 판만 지원합니다. Epic 판은 확인하지 않았습니다.
- 시어터 모드는 별도 실행 파일이고 Panacea가 지원하지 않아 한글화하지 않았습니다.
- 모든 장면을 게임 안에서 확인하지는 못했습니다. 특수 연출 대사 등 확인이 필요한 목록은 [docs/known-issues.md](docs/known-issues.md)에 있고, 플레이 제보로 수정할 예정입니다.
- 공식 한국어 자막이 나오면 고유명사 표기를 다시 맞출 예정입니다.
- 실행 중 메모리를 고치는 기능 때문에 일부 백신이 실행 파일을 오탐할 수 있습니다.

## 8. 라이선스와 고지

- 이 프로젝트는 비공식 팬 번역이며 Square Enix, Disney와 관계가 없습니다. 게임 데이터의 권리는 각 권리자에게 있습니다.
- [tools/pkgextract.py](tools/pkgextract.py)의 형식 처리는 OpenKH(Apache License 2.0)의 `OpenKh.Egs`를 Python으로 옮긴 것입니다.
- 배포 파일에 포함되는 `OpenKH.Panacea.dll`은 OpenKH의 것입니다([LICENSE](third_party/LICENSE-OpenKH.txt), [NOTICE](third_party/NOTICE-OpenKH.txt)).
- 이 저장소의 코드, 문서, 한국어 번역문은 [Apache License 2.0](LICENSE)을 따릅니다([NOTICE](NOTICE)). 라이선스는 이 프로젝트가 직접 만든 부분에만 적용되며, 게임 원작의 이름·설정·내용에 대한 권리를 부여하지 않습니다.
