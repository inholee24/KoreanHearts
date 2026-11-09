# 추출·변환·적용 및 검증 절차

대상: KH1 (KINGDOM HEARTS FINAL MIX), Steam PC판 HD 1.5+2.5 ReMIX.

## 환경 (실측 확인됨)

| 항목 | 값 |
|---|---|
| OpenKH | 릴리스 바이너리 `release2-1625` (`D:\Projects\openkh`, 소스 저장소 아님) |
| 게임 설치 | `D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-` |
| 추출 데이터 | `D:\Projects\openkh\data\kh1` (약 19.5 GB) |
| 적용 디렉터리 | `D:\Projects\openkh\mod\kh1` |
| 모드 소스 | `D:\Projects\openkh\mods\kh1\<모드명>\` |
| 버전 관리 | **없음** (Git 저장소가 아님) |

`D:\Projects\openkh`는 `C:\openkh`의 복사본이다. `C:\openkh`는 폴백으로 남아 있으나 현재 파이프라인은 D만 사용한다.

## 파이프라인

### 1. 추출 — OpenKH Mods Manager

`OpenKh.Tools.ModsManager.exe`. 설정은 [../mods-manager.yml](../mods-manager.yml)에 있다.

```yaml
pcVersion: Steam
pcReleaseLocation: D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-
gameDataPath: D:\Projects\openkh\data
gamesToExtract: [kh2, kh1]
skipRemastered: false
panaceaInstalled: true
launchGame: kh1
```

이미 실행되어 `data\kh1`이 존재한다. **재실행할 이유가 없다.**

### 2. 적용 — Panacea 런타임 후킹

게임 폴더에 Panacea가 `DBGHELP.dll`로 설치되어 있다 (`OpenKH.Panacea.dll`과 SHA256 동일).

```text
D:\SteamLibrary\...\ReMIX-\panacea_settings.txt
  mod_path=D:\Projects\openkh\mod
  enable_cache=true
```

게임은 실행 중 `mod_path` 이하에 같은 상대 경로의 파일이 있으면 원본 대신 그것을 읽는다.

**IDX/IMG 재패킹 과정은 없다.** 파일을 `mod\kh1\` 아래 원본과 같은 상대 경로에 두면 끝이다.

```text
data\kh1\exchange\UK_item_shop_msg.bin        원본
 mod\kh1\exchange\UK_item_shop_msg.bin        이것이 대신 읽힘
```

### 3. 실행

ModsManager의 **Run Only**를 쓴다.

> **Build / Build and Run 을 쓰지 말 것.** `mod\` 전체를 `mods\` 정의로 다시 만들어 수동 배치한 파일을 덮어쓴다. 2026-07-22 작업 중 실제로 발생했다 ([work-history.md](work-history.md)).

현재 `mods-KH1.txt`에 활성화된 모드는 `KH1 Korean Test` 하나이고, 그 `mod.yml`은 `exchange\UK_item_shop_msg.bin` **한 개만** 정의한다. 지금 `mod\kh1`에 있는 23개 파일은 ModsManager가 만든 것이 아니라 실험 패키지를 직접 푼 결과다.

## 작업 루프

```text
1. 현재 mod\kh1 상태 백업
2. data\kh1 의 원본을 기준으로 대상 파일 수정
3. mod\kh1 의 같은 상대 경로에 배치
4. ModsManager -> Run Only
5. 화면 결과 확인
6. 결과를 docs/work-history.md 에 기록      <- 반드시
```

6번을 빠뜨려서 마지막 실험 결과가 유실되었다. 실행 결과는 성공/실패와 무관하게 기록한다.

## 검증

Git이 없으므로 diff 대신 다음을 쓴다.

- **해시 비교**: 원본(`data\`) / 배치본(`mod\`) / 백업의 SHA256
- **길이 불변 확인**: 메시지 `.bin`은 오프셋 인덱스를 쓰므로 전체 길이를 바꾸지 않는다
- **바이트 diff**: 의도한 오프셋만 변했는지 확인
- 실행 후 화면 확인

## 대사 한글화 파이프라인 (2026-10-29, 26차)

번역은 표 하나에 쓰고, 적용본은 원본 `data\kh1`에서 매번 새로 만든다. 파이썬은 `D:\Projects\openkh_venv\Scripts\python -I -X utf8` (`-I`는 `PYTHONIOENCODING`을 무시하므로 콘솔 한글은 `-X utf8`로).

```text
1. tools/evmsg_export.py      원본 UK/US .binl -> translation/kh1_evmsg.tsv (고유 메시지 6,135줄)
                              다시 실행해도 ko 열은 key 로 보존된다
2. translation/kh1_evmsg.tsv  ko 열에 번역 (형식은 아래)
3. tools/build_ko.py          확인만. 새 글자 수/배정/바뀔 파일 수 출력
4. (백업)                      mod 의 UK/US .binl, UK_kanji.knj, UK_kanji_knj0.dds
5. tools/build_ko.py --apply  DDS(1024 배치) + 폭 표 + .binl 을 mod\kh1 에 쓴다
6. tools/re/mem.py tex2x 14400 new   (백그라운드) 새로 켜는 게임의 글꼴 텍스처를 1024 로
7. ModsManager -> Run Only, 화면 확인, work-history 기록
```

번역 표기 (`tools/evmsg.py` `show`/`encode`): 원문 열 `en` 과 같은 형식.

| 표기 | 뜻 |
|---|---|
| `[0A 00 00 00]` 등 | 제어 코드. 원문 것을 그대로 둔다 (`[0B 00 23 00]` = 선택지 들여쓰기 등) |
| `\n` | 줄바꿈 (`0x02`) |
| `{7A}` | 문자표에 없는 1바이트 글자 (아이콘 등). `[ ] < >` 글자도 `{76}`~`{79}` 로 쓴다 |
| `<04>`, `<00>` | 메시지 끝. 원문 것을 지킨다 |
| 그 외 | 글자. 원본 문자표(영문, 숫자, `!?.,…'"~()` 등)에 없는 글자(한글)는 빌드가 칸을 배정해 그린다 |

- 같은 원문은 한 줄이다. 같은 원문을 특정 위치에서만 다르게 번역하려면 `translation/kh1_evmsg_loc.tsv` (열: file idx en ko) 에 적는다 (49차, key 별 번역보다 우선. en 이 원본과 다르면 빌드가 멈춘다).
- 한글 칸 상한: en 배치 918, jp 배치(--layout jp, 28차 실험) 1335. 넘으면 빌드가 멈춘다.
- `.evdl` 안의 메시지 사본은 건드리지 않는다 (게임은 `.binl` 을 표시에 쓴다, 18차). 선택지 창 폭(`op4`)은 `tools/patch_binl_seq.py --same-length` 로 따로 고친다 (24차).

## 도구 제약 (확인됨)

- **OpenKH에는 KH1 메시지 편집 도구가 없다.** `OpenKh.Command.MsgTool`은 KH2 전용이며 인코더가 `eusys / euevt / jpsys / jpevt` 4종뿐이다. `OpenKh.Tools.Kh2TextEditor`도 KH2 전용이다. → 위 파이프라인(`tools/`)을 쓴다.

## 백업

버전 관리가 없으므로 변경 전 백업이 유일한 되돌리기 수단이다. 최소한 다음을 남긴다.

- 수정 대상 파일의 원본 사본
- `mod\kh1` 전체 (파일 23개, DDS 포함 약 1.3 GB — 큰 DDS는 해시만 기록해도 된다)

## 사고 기록: ModsManager "Fast restore" (2026-09-21)

실수로 `Fast restore`를 눌러 **`D:\Projects\openkh\mod\kh1` 전체가 삭제**되었다 (남은 것은 `mod\kh2\patch-package-map.txt`뿐).

확인된 영향 (파일 시각과 해시 근거):

| 대상 | 상태 |
|---|---|
| `D:\Projects\openkh\mod\kh1\**` | **삭제됨** (실험 상태 전부) |
| `D:\Projects\openkh\data\kh1` | 무사. 핵심 4개 파일 해시가 원본과 일치, 파일 66,522개 |
| `C:\openkh\mod\kh1` | 무사. 23개 파일, 2026-07-22 기준선 그대로 |
| 게임 `panacea_settings.txt` | 05:54:17에 다시 쓰였으나 내용 동일 (`mod_path=D:\Projects\openkh\mod`) |
| 게임 `STEAM\dt\KH1Movie\LOP.mp4` (277MB) | **05:53:28에 다시 쓰임.** 같은 폴더의 다른 영상은 2025-07-20 원본 날짜. 복구 동작이 이 파일을 건드린 것으로 보이나 무엇을 했는지 확인하지 못했다 |

**LOP.mp4는 검증하지 못했다.** Steam의 게임 파일 무결성 검사로 확인하는 것이 안전하다.

복구 방법: 스크립트 `rebuild_test8.ps1`(스크래치패드)이 `C:\openkh\mod\kh1`을 기준선으로 복사하고 8차 상태(표, `UK_kanji.knj` 폭 테이블 11바이트, 메시지 24바이트, 라벨 DDS 20개)를 다시 만든다. 이 과정은 약 20초 걸렸고 역조회로 검증했다.

**교훈**

- ModsManager의 `Restore`, `Fast restore`, `Build`는 `mod\kh1`을 지운다. 손으로 배치한 실험 파일이 모두 사라진다.
- 실험 상태를 재생성하는 스크립트를 항상 파일로 둔다. 이번에는 백업 스크립트가 있어서 복구할 수 있었다.
- 대용량 DDS(각 67MB, 20개)는 백업하지 않고 **기준선 + 스크립트**로 재생성한다.
- ModsManager를 실험 중에는 닫아 둔다.