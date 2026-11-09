# KoreanHearts: 킹덤 하츠 한글화 프로젝트

PC Steam 판 *KINGDOM HEARTS -HD 1.5+2.5 ReMIX-* 의 타이틀을 한국어로 플레이할 수 있게 만드는 비공식 한글화 프로젝트입니다. 설치 프로그램 하나로 타이틀별 한글 패치를 골라 설치하고 제거할 수 있습니다.

| 타이틀 | 상태 | 폴더 |
|---|---|---|
| 킹덤 하츠 1 (KINGDOM HEARTS FINAL MIX) | 배포 중 | [kh1/](kh1/) |
| 킹덤 하츠 Re:Chain of Memories | 번역·빌드 완료, 게임 확인 전 (아직 배포 안 함) | [recom/](recom/) |

> **이 저장소와 배포 파일은 패치일 뿐이며 게임을 포함하거나 배포하지 않습니다.** 정품 게임이 필요합니다. 게임 원본 데이터는 들어 있지 않습니다. Square Enix, Disney와 관계없는 비공식 팬 번역입니다. 사용 전에 [사용자 유의 사항](#사용자-유의-사항)을 읽어 주세요.

아래 1~5절과 7절은 첫 타이틀인 **킹덤 하츠 1** 의 작업 기록입니다. Re:COM 진행 상황은 [recom/docs/](recom/docs/) 에 있습니다.

## 킹덤 하츠 1

**KINGDOM HEARTS FINAL MIX** (PC Steam 판 *KINGDOM HEARTS -HD 1.5+2.5 ReMIX-*) 한글 패치입니다.

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
3. 성공과 실패를 모두 [docs/work-history.md](kh1/docs/work-history.md)에 남깁니다. 기각한 가설은 "재시도하지 말 것"에 따로 모읍니다.

이 방식으로 게임 내 실험을 55차까지 진행했습니다. 9차 실험에서는 3~8차의 "글자가 안 보인다"는 결과가 코드 경로 문제가 아니라 **글자 색 문제**였다는 것이 드러났습니다. 그래서 앞선 결론을 무효로 하고 다시 쌓았습니다. 이런 판단 과정도 모두 기록에 남아 있습니다.

### 실행 파일 분석 (정적 + 동적)

데이터만으로 설명되지 않는 동작은 게임 실행 파일을 디스어셈블해 확인했습니다.

- **분석 도구를 직접 만들었습니다.** 함수 15,808개, 호출·참조·포인터 표를 색인하는 도구([tools/re/](kh1/tools/re/))를 만들었습니다. 알아낸 함수와 변수의 의미는 지식 베이스([tools/re/names.tsv](kh1/tools/re/names.tsv))에 쌓았습니다.
- **실행 중인 게임의 메모리를 확인했습니다.** 창 크기, 글꼴 표, 텍스처 크기를 읽어 정적 분석의 추론을 검증했습니다.
- **분석으로 찾은 것:**
  - 메시지 2바이트 코드 규칙: `((b0<<8)|b1) - 0x1820`
  - 디코더 버그: 특정 첫 바이트가 공백으로 처리되는 문제
  - 선택지 창 폭의 실제 출처: 이벤트 스크립트 명령의 즉값
  - 시스템 글꼴 표의 버퍼 구조

결과는 [docs/exe-analysis.md](kh1/docs/exe-analysis.md)와 [docs/file-formats.md](kh1/docs/file-formats.md)에 정리했습니다. 문서 전체에서 `확정`(디스어셈블이나 실측으로 확인)과 `추론`을 구분해 적었습니다.

### 글자 용량 문제의 해결

- **대화창 글꼴:** 일본어판이 같은 실행 파일 안에서 더 촘촘한 글꼴 배치(1,764칸)를 쓴다는 것을 찾았습니다. 그래서 영어 경로에서도 일본어판 배치를 쓰게 했습니다.
  - 한글 글리프는 맑은 고딕으로 렌더링합니다.
  - 원본과 같은 테두리와 알파 계조를 넣습니다.
  - 게임의 축소 렌더링에서 획 굵기가 고르게 보이도록 미리 보정합니다.
- **시스템 글꼴:** 텍스처를 2048로 확장했습니다. 글꼴 표를 원래 레코드 수의 약 2배(2,016개)로 늘려 게임 메모리에 연결합니다.
- **실행 파일 원본은 바꾸지 않습니다.** 필요한 값 8개는 게임 실행 중에 메모리에 씁니다. 게임이 값을 다시 초기화하면 다시 씁니다.

### 번역과 용어

- **용어 기준:** 고유명사는 시리즈 한국어 정발작(KH3)의 표기를 따릅니다. 예: 도날드, 홀로우 바스티온, 킹덤 체인. 용어집은 [docs/terminology.md](kh1/docs/terminology.md), 번역 원칙은 [docs/translation-rules.md](kh1/docs/translation-rules.md)입니다.
- **엔진 제약을 번역 규칙으로:**
  - 선택지는 줄 수를 유지합니다.
  - 아이템 이름이 들어가는 자리 뒤에는 받침에 따라 바뀌는 조사를 붙이지 않습니다.
  - 고정 크기 말풍선은 원문 용량을 넘지 않게 줄을 나눕니다.
  - 가운데 정렬 자막은 번역문 폭에 맞춰 위치를 다시 계산합니다.
- **화자와 장면:** 캐릭터별 말투, 같은 대사가 여러 월드 파일에 반복되는 경우, 퍼즐 풀이에 영어 알파벳이 필요한 장면 등을 장면 단위로 판단했습니다.
- **번역 방식:** 초안은 AI(Claude)로 작성했습니다. 용어집, 일괄 검사 도구([tools/tr_batch.py](kh1/tools/tr_batch.py)), 빌드 검증으로 일관성을 관리합니다.

### 검증 자동화

사람이 모든 장면을 플레이해 확인할 수 없는 부분은 도구로 확인합니다.

- [tools/verify_build.py](kh1/tools/verify_build.py)
  - 빌드한 메시지 파일 2,000여 개를 원본과 하나씩 대조합니다.
  - 바뀐 메시지가 모두 번역이 있는 원문이고, 글자 표로 해독했을 때 번역문과 정확히 같은지 확인합니다.
  - 확인 대상은 메시지 약 75만 개입니다.
- [tools/bubble_check.py](kh1/tools/bubble_check.py): 이벤트 스크립트를 실행 파일 규칙대로 따라가 각 대사가 어떤 크기의 말풍선에 뜨는지 찾고, 실제 빌드 결과를 게임과 같은 방식으로 재서 넘치는 대사를 찾습니다.
- [tools/sysfont_sim.py](kh1/tools/sysfont_sim.py): 실행 파일의 규칙대로 UI 글꼴을 그려 봅니다. 게임을 켜지 않고 결과를 미리 확인할 수 있습니다.

## 3. 배포 설계: 원본 데이터 없는 패치

배포 파일과 이 저장소에는 **게임 원본 파일도, 영어 원문도 들어 있지 않습니다.**

- **번역 표는 `키 + 한국어`만 저장합니다.** 영어 원문은 설치할 때 사용자 PC의 게임에서 다시 채웁니다([tools/tables.py](kh1/tools/tables.py)).
- **설치 프로그램이 한글 파일을 사용자 PC에서 직접 만듭니다.**
  - 게임 패키지(.hed/.pkg)에서 필요한 파일 2,281개만 꺼냅니다([tools/pkgextract.py](kh1/tools/pkgextract.py), OpenKH 형식 처리를 Python으로 옮김).
  - 빌드와 검증을 거친 뒤, 꺼낸 원본은 지웁니다.
  - 게임 원본 파일은 수정하지 않습니다. 결과물은 OpenKH Panacea를 통해 읽힙니다.
- **사용자가 하는 일은 실행 파일 하나를 실행하고 버튼 두 개를 누르는 것뿐입니다.** (타이틀 선택 → "설치·업데이트" → "게임 실행")
- **번역을 고쳐도 설치 프로그램을 다시 받을 필요가 없습니다.** 설치 프로그램은 실행할 때 이 저장소 `main`의 최신 커밋을 확인합니다. 새 커밋이 있으면 번역 표와 빌드 도구(`kh1/translation/src`, `tools`)를 받아 그것으로 다시 빌드합니다([installer/update.py](installer/update.py)). 설치 프로그램 자체가 바뀌어야 하는 변경은 [installer/update.json](installer/update.json)의 `min_app`을 올립니다.
- **설치 프로그램도 스스로 업데이트합니다 (0.5.0 부터).** 실행할 때 이 저장소의 최신 GitHub 릴리스를 확인해서, 더 높은 판이면 릴리스 zip을 받아 실행 파일을 바꾸고 다시 시작합니다([installer/selfupdate.py](installer/selfupdate.py)). 받은 파일은 크기·sha256(GitHub 자산 digest)을 확인하고, 새 실행 파일을 한 번 시험 실행해 보고한 버전이 릴리스 태그와 같을 때만 바꿉니다. 실패하면 지금 판으로 계속합니다.
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
                    한글 파일 (KoreanHearts/mod/kh1) ◀── Panacea 가 게임에 공급
                                       + 실행 중 메모리 패치 (글꼴 배치·표 확장·영상 자막)
```

## 4. 결과

- 전 월드의 대사, 이벤트 자막, 상점·합성·콜로세움 메시지, 메뉴, 아이템·어빌리티 설명, 지미니 메모, 구미 차고, 설정 메뉴, 장소 이름을 한국어로 표시합니다.
- 타이틀 화면, 전투 명령 메뉴, 메인 메뉴, 월드 제목, 구미 미션 화면 등 그림 속 글자 67장을 한글로 바꿨습니다.
- 영상(오프닝·엔딩·타이틀 대기 영상·숨겨진 영상)에 한국어 자막을 넣었습니다. 게임에 언어별 영상 자막 기능이 있으나 영어판은 대부분 비어 있다는 것을 실행 파일 분석으로 찾아, 그 칸에 한국어 자막 표를 연결합니다. 영어판에는 없던 소라의 오프닝 독백 자막도 나옵니다.
- 게임 내 확인 장면 예:
  - 타이틀
  - 대사 창, 선택지
  - 전투 명령 메뉴, 일시 정지
  - 메뉴 이름·설명
  - 구미 차고 도움말
  - 설정 메뉴
  - 장소 이름
  - 확장 표의 글자(황, 흩 등)
  - 오프닝 영상 자막

## 5. 저장소 구조

| 경로 | 내용 |
|---|---|
| [kh1/translation/src/](kh1/translation/src/) | KH1 번역 표 (키와 한국어만). 번역의 원본 |
| [kh1/tools/](kh1/tools/) | KH1 추출·변환·빌드·검증 도구 |
| [kh1/tools/re/](kh1/tools/re/) | KH1 실행 파일 분석 도구, 실행 중 메모리 패치 (`mem.py`) |
| [kh1/docs/](kh1/docs/) | KH1 파일 형식, 실행 파일 분석, 작업 기록, 용어집(시리즈 공통), 알려진 문제 |
| [recom/](recom/) | Re:COM (같은 구성: `docs/`, `tools/`, `translation/src/`) |
| [installer/](installer/) | 공용 설치·실행 프로그램 (`app.py`, tkinter, 타이틀별 설치·제거), PyInstaller 설정, 배포 빌드 스크립트 |
| [third_party/](third_party/) | 제3자 라이선스 전문 (`licenses/`). `OpenKH.Panacea.dll`은 OpenKH 릴리스에서 복사 |

저장소에 넣지 않는 것(`.gitignore`, 타이틀 폴더마다): `data/`(꺼낸 원본), `mod/`(결과물), `translation/*.tsv`(원문이 들어간 전체 표), `translation/build/`, 게임 화면 캡처.

새 타이틀을 추가할 때: 타이틀 폴더(`<id>/tools`, `<id>/translation/src`, `<id>/docs`)를 만들고, `installer/app.py` 의 `TITLES`·`BUILDERS` 와 `installer/koreanhearts.spec` 의 `TITLE_DIRS` 에 등록합니다. 도구 모듈 이름은 다른 타이틀과 겹치면 안 됩니다(한 실행 파일에 최상위 모듈로 묶임).

### 주요 문서

- [docs/work-history.md](kh1/docs/work-history.md): 1~55차 실험의 가설, 변경, 결과, 판단 근거
- [docs/exe-analysis.md](kh1/docs/exe-analysis.md): 실행 파일 분석 결과(함수 주소, 구조체, 분석 도구 사용법)
- [docs/file-formats.md](kh1/docs/file-formats.md): 메시지 인코딩, 글꼴 표, 텍스처 배치, 패키지 형식
- [docs/build-process.md](kh1/docs/build-process.md): 추출, 빌드, 적용, 검증 절차
- [docs/known-issues.md](kh1/docs/known-issues.md): 해결한 문제와 남은 확인 항목

## 6. 사용 방법

### 설치 (사용자)

배포 zip의 `KoreanHearts.exe`를 실행하고, 설치할 타이틀을 고른 뒤 "선택한 타이틀 설치·업데이트" → "게임 실행"을 누릅니다. 제거도 타이틀별로 고를 수 있습니다. 설치 전에 아래 유의 사항 요약을 보여 주고 동의를 받습니다. 게임하는 동안 이 창은 열어 둡니다. 자세한 내용은 [installer/README-release.txt](installer/README-release.txt)에 있습니다.

### 사용자 유의 사항

1. **패치일 뿐입니다.** 게임 본편을 포함하거나 배포하지 않습니다. 정품 게임(Steam 판)이 있어야 쓸 수 있습니다.
2. **원본 데이터가 없습니다.** 배포 파일에는 게임 파일, 그림, 소리, 영어 원문이 들어 있지 않습니다. 설치할 때 사용자 PC의 게임 파일을 읽어 한글 파일을 그 PC에서 만듭니다.
3. **만들어진 파일을 공유하지 마세요.** 설치로 생긴 `KoreanHearts` 폴더의 파일은 게임 데이터를 바탕으로 한 것이라 재배포하면 권리자의 권리를 침해할 수 있습니다. 다른 사람은 이 패치를 받아 직접 설치하면 됩니다.
4. **비공식입니다.** Square Enix, Disney 등 권리자와 관계가 없고 승인을 받지 않았습니다. 이 패치에 관한 문의를 게임 회사나 Steam에 하지 마세요.
5. **무료입니다.** 돈을 받고 판매되거나 게임과 함께 묶여 배포된다면 이 프로젝트의 배포가 아닙니다.
6. **사용 책임은 사용자에게 있습니다.** 게임 원본 파일은 바꾸지 않지만, 모드 로더(OpenKH Panacea)를 게임 폴더에 설치하고 게임 실행 중 메모리 값을 고칩니다. 게임·플랫폼 이용약관에 관한 판단은 사용자가 해야 합니다.
7. **보증이 없습니다.** Apache License 2.0 제7·8조에 따라 있는 그대로 제공됩니다. 게임 오류나 세이브 데이터 손상에 책임지지 않으니 세이브 데이터를 미리 백업하세요.
8. **개인 정보를 보내지 않습니다.** 설치 프로그램은 실행할 때 GitHub(이 저장소)에서 최신 번역이 있는지 확인하고 받기만 합니다. "게임 실행"은 Steam에 실행만 요청합니다.
9. **백신 오탐 가능성이 있습니다.** 게임 메모리를 고치는 기능 때문에 일부 백신이 실행 파일을 위험하다고 판단할 수 있습니다.
10. **권리자가 요청하면 배포를 중단합니다.** 공식 한국어판이 나오면 공식판 이용을 권합니다.

### 개발

Python 3.13 + Pillow가 필요하고, 맑은 고딕(`C:\Windows\Fonts\malgun*.ttf`)이 있어야 합니다.

```text
1. python kh1/tools/pkgextract.py "<게임 폴더>" .     필요한 원본만 kh1/data/kh1, kh1/data/settingmenu 로 (약 2.2GB)
2. python kh1/tools/tables.py expand                   kh1/translation/src + 원본 -> 전체 표 kh1/translation/*.tsv
3. (번역 작업: kh1/translation/*.tsv 의 ko 열, kh1/tools/tr_batch.py)
4. python kh1/tools/build_ko.py --layout jp --apply    대사·메뉴·글꼴 -> kh1/mod/kh1
   python kh1/tools/imgtext.py --apply                  그림 속 글자
   python kh1/tools/settingmenu.py --apply              설정 메뉴
   python kh1/tools/evdl_patch.py --apply               상점 선택지 창 폭
5. python kh1/tools/verify_build.py                     '문제 0' 이어야 함
   python kh1/tools/bubble_check.py                     말풍선 넘침 '넘침 0'
6. python kh1/tools/tables.py strip                     커밋 전에 kh1/translation/src 갱신
   python kh1/tools/tables.py check                     strip -> expand 가 전체 표와 같은지
```

- **게임에서 확인하려면:** Panacea의 `panacea_settings.txt`에서 `mod_path`를 이 저장소의 `kh1/mod`로 둡니다. 그다음 `python kh1/tools/re/mem.py tex2x 14400 jp`를 켠 채 게임을 실행합니다.
- **배포 파일 만들기:** `powershell -ExecutionPolicy Bypass -File installer/build_release.ps1`을 실행하면 `release/KoreanHearts-<버전>.zip`이 나옵니다.
- **번역 업데이트 배포:** `main`에 push하면 사용자의 설치 프로그램이 다음 실행 때 받아 갑니다. `tables.py strip`으로 `kh1/translation/src`를 갱신한 뒤 push합니다. 설치 프로그램은 타이틀별 파일 내용으로 새 번역을 판단하므로, 한 타이틀만 고친 커밋은 다른 타이틀 사용자에게 업데이트를 묻지 않습니다(0.4.0 부터). `installer/app.py`·`installer/update.py`를 고쳤거나 실행 파일에 묶이지 않은 라이브러리가 새로 필요하면 `VERSION`과 `installer/update.json`의 `min_app`을 함께 올리고 새 릴리스를 만듭니다.
- **설치 프로그램 릴리스 규칙 (자동 업데이트가 이것을 찾습니다):** 태그는 `v` + `installer/app.py`의 `VERSION`(예: `v0.5.0`), 자산은 `build_release.ps1`이 만든 `KoreanHearts-<버전>.zip` 그대로 올립니다. 초안·시험판(pre-release)은 받지 않습니다. 태그와 실행 파일의 `VERSION`이 다르면 사용자 쪽에서 바꾸지 않습니다. `min_app`을 올린 커밋은 그 릴리스를 올린 뒤에 `main`에 push하는 것이 좋습니다(먼저 push하면 그동안 사용자는 받아 둔 번역을 씁니다).

## 7. 한계와 남은 일

- Steam 판만 지원합니다. Epic 판은 확인하지 않았습니다.
- 시어터 모드는 별도 실행 파일이고 Panacea가 지원하지 않아 한글화하지 않았습니다.
- 모든 장면을 게임 안에서 확인하지는 못했습니다. 특수 연출 대사 등 확인이 필요한 목록은 [docs/known-issues.md](kh1/docs/known-issues.md)에 있고, 플레이 제보로 수정할 예정입니다.
- 공식 한국어 자막이 나오면 고유명사 표기를 다시 맞출 예정입니다.
- 실행 중 메모리를 고치는 기능 때문에 일부 백신이 실행 파일을 오탐할 수 있습니다.

## 8. 라이선스와 저작권

### 이 프로젝트

이 저장소의 코드, 문서, 한국어 번역문은 [Apache License 2.0](LICENSE)을 따릅니다. 고지 전문은 [NOTICE](NOTICE)에 있습니다. 라이선스는 이 프로젝트가 직접 만든 부분에만 적용되며, 게임과 그 내용에 대한 어떤 권리도 부여하지 않습니다.

### 게임 저작권

이 프로젝트는 비영리 비공식 팬 번역입니다. Square Enix, Disney, Valve 등 아래 권리자와 관계가 없고, 이들의 승인을 받지 않았습니다. 정품 게임이 필요합니다. 저장소와 배포 파일에는 게임 원본 데이터(파일, 그림, 소리, 원문)가 들어 있지 않습니다.

게임에 표시되는 저작권 고지는 다음과 같습니다(게임 내 표기 그대로).

```text
© Disney.

Tarzan™ Owned by Edgar Rice Burroughs, Inc.
and Used by Permission
Copyright © 2002 Edgar Rice Burroughs, Inc.
and Disney Enterprises, Inc. All Rights Reserved.

Characters from FINAL FANTASY video game series:
© 1990,1997,1999,2001,2002 SQUARE ENIX CO., LTD.
All Rights Reserved.
SQUARE ENIX and the SQUARE ENIX logo are registered
trademarks or trademarks of Square Enix Holdings Co., Ltd.
```

- KINGDOM HEARTS, FINAL FANTASY와 등장인물·지명·아이템 이름·이야기·대사의 권리는 Disney 및 Square Enix와 각 라이선서에게 있습니다.
- 한국어 고유명사는 시리즈 한국어 정발판의 표기를 따랐으며, 그 표기의 권리도 각 권리자에게 있습니다.
- Steam은 Valve Corporation의 상표입니다. Windows와 맑은 고딕(Malgun Gothic)은 Microsoft Corporation의 상표입니다.

### 글꼴

글꼴 파일은 배포하지 않습니다. 설치 프로그램이 사용자 PC에 설치된 맑은 고딕(`C:\Windows\Fonts\malgun*.ttf`)으로 한글 글자를 그 자리에서 그립니다.

### 제3자 소프트웨어

| 구성 요소 | 쓰임 | 라이선스 |
|---|---|---|
| [OpenKH](https://github.com/OpenKH/OpenKh) | `kh1/tools/pkgextract.py`가 `OpenKh.Egs`의 형식 처리를 옮김. 배포 파일에 `OpenKH.Panacea.dll`(수정하지 않음) 포함 | Apache 2.0 |
| Python 3.13 | 설치 프로그램 실행 환경 | PSF License |
| Pillow 및 묶인 라이브러리(FreeType, libjpeg-turbo, libpng, libtiff, libwebp, OpenJPEG, Little CMS, HarfBuzz 등) | 글자 렌더링, 그림 처리 | MIT-CMU 외 각 라이브러리 라이선스 |
| Tcl/Tk | 설치 프로그램 화면 | Tcl/Tk License |
| OpenSSL 3, libffi, expat, bzip2, xz, mpdecimal, zlib | Python 표준 라이브러리 구성 요소 | Apache 2.0 / 각 허용 라이선스 |
| Microsoft Visual C++ 런타임, UCRT | 실행 환경 | Microsoft 재배포 조건 |
| PyInstaller 부트로더 | 단일 실행 파일 | GPL-2.0+ (부트로더 예외) |

라이선스 전문은 [third_party/licenses/](third_party/licenses/)에 있고, 배포 zip의 `licenses` 폴더에도 들어 있습니다.
