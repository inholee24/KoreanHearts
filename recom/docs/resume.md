# 재개 안내 (세션이 끊기면 여기부터)

작업 위치: `D:\Projects\recom-korean` (KoreanHearts 저장소 `recom` 브랜치 worktree, 커밋 없음).
먼저 읽을 것: [kh1-lessons.md](kh1-lessons.md) 0절, [conversation-lessons.md](conversation-lessons.md), [file-formats.md](file-formats.md).
파이썬: `D:\Projects\openkh_venv\Scripts\python.exe -I -X utf8 recom/tools/<도구>.py` (저장소 루트에서).
원본 데이터: 환경 변수 `RECOMKO_DATA` (개발: `D:\Projects\openkh\data\Recom`). 없으면 `recom/data/recom`.

## 진행 단계 (2026-11-05 시작)

| 단계 | 상태 | 도구 / 결과 |
|---|---|---|
| 1. 번역 표 추출 | **완료** | `recom_table.py expand/strip/check` -> `recom/translation/recom_ctd.tsv` (3,373줄). 표기 `recom_text.py`, 왕복 `recom_roundtrip.py` (426 파일 바이트 동일) |
| 2. 빌드 (두 글꼴 공통 배정) | **완료** (번역 0 으로 확인) | `recom_build.py [--apply]`, 글자 그리기 `recom_font.py` |
| 3. 검증 | **완료** | `recom_verify.py` (문제 0 이어야 함) |
| 4. 시뮬레이터 (게임 규칙대로 그려 보기) | **완료** | `recom_sim.py <ctdl> [번호]` -> translation/build/sim/. 공백 = 크기x3/8 (exe+화면 측정) |
| 5. 작은 표본 전 과정 시험 | **완료** (게임 확인은 마지막에 묶어서) | FO0111 등 28줄 -> 빌드 97자, 메시지 126 / 파일 30, verify 문제 0, 시뮬레이터 sys/evt 확인 |
| 6. 번역 일감 도구 | **완료** | `recom_tr.py stats / next N [경로] / apply <파일> [--force] / show <key|문자열>`. 일감 파일은 `key | 번역` 형식 |
| 7. CTD 번역 | **완료** (2026-11-05) | 3,365 / 3,373 (남은 8 = 개발용 Dummy* 7 + QUESTION, 일부러 원문 유지). 작업 파일 b000~b035. 한글 951자 / sysfont 963 칸. `recom_build.py --apply` 426 파일, `recom_verify.py` 문제 0 |

## 다음에 할 일

0. **CTD 번역 이후 (2026-11-05 기준 다음 단계):**
   - ~~말풍선이 글 길이에 맞춰 늘어나는지~~ **확인됨 (2026-11-05):** 창 크기는 레이아웃 데이터 값이고 게임이 늘리지 않음 (추론 포함, file-formats.md "레이아웃 사각형"). 빌드가 `recom_layoutfix` 로 창을 넓혀 준다 (고유 183 레이아웃, 최대 +38px). 따라서 --force 한 줄도 창 밖으로 나가지 않게 된다.
   - 마지막 게임 확인 목록에 추가: 늘어난 창 틀 그림이 자연스러운지 (9분할 추정), 말꼬리 위치. 예: WORLD 대사 중 폭이 많이 는 레이아웃 (`recom_layoutfix` 결과 상위).
   - 한글 칸 (2026-11-09 갱신): sysfont 899 / CTD 한글 855 = 여유 44, evtfont 1,280 / 전체 928. 번역을 고칠 때 `recom_tr.py stats` 확인 (칸 수는 recom_capacity 로 계산).
   - **MVS 이벤트 장면 자막 번역: 완료 (2026-11-05, b036~b049, 1,713 줄).** (아래는 참고용 설명) 파이프라인 연결 끝 (표·빌드·검증·왕복이 .ctdl + MVS 를 함께 다룸, file-formats.md "영상 자막 MVS"). 남은 줄 `recom_tr.py next 200 remastered/FORM/5` (파일 FO5011 부터 장면 순). 일감 파일 b036_mvs~. 자막 폭 규칙은 고정 창 400px / 2줄 (apply 가 자동 적용).
     자막에만 나오는 한글은 evtfont 만 (칸 1,339). `recom_tr.py stats` 의 "CTD 에 나옴" 은 sysfont 칸(899) 이하, 전체는 evtfont 칸(1,280) 이하여야 한다.
   - 설정 메뉴: 완료 (`recom_settingmenu.py --apply`, 환경 변수 RECOMKO_SETTINGMENU).
   - 그림 (.imz): 사용자 결정 = 전부. **완료** (도움말 100: `recom_helpstock.py apply`, 나머지 39: `recom_imgtext.py apply`).
   - 설치기 연동: **완료** (0.5.0, `recom_fullbuild.py`, 실행 파일로 임시 게임 폴더에 설치·제거 시험 통과).
   - **게임 확인 1차 완료 (2026-11-09, work-history 같은 날짜):** 타이틀 메뉴·설정 메뉴(키 설정 포함)·첫 자막·말풍선·"아니요"·튜토리얼·HUD·"가드"·카드 획득·월드 선택·일시 정지 = 확인.
     이 과정에서 타이틀 PNG, 설정 메뉴 경로(mod/recom/ctd, font — uk/ 없음), 일시 정지 칸 잘림(.lad 사각형 box)을 고침.
     **게임 확인 2차 (2026-11-09, 사용자 세이브 01 로드, 저장 안 함):** 메인 메뉴·덱 편집·덱 이름 변경·상태·메모·월드 카드 확인.
     덱 편집 "하03"·이름 입력 키보드 한글 = 글꼴 칸 충돌 -> `recom_capacity.GAME_CODES` 로 고치고 드문 글자 93줄 고쳐 씀 (b050). 게임에서 정상 확인.
     사용자 세이브: 문서 폴더 `My Games\KINGDOM HEARTS HD 1.5+2.5 ReMIX\Steam\<SteamID>\KHReCoM_WW.png` (불러오기 전 백업, 게임에서 저장하지 말 것).
     취소 = Backspace. 타이틀: 첫 Enter = 영상 건너뛰기, 다음 Enter 는 새 게임 메뉴. 로드 = 타이틀에서 아래 1칸.
     남은 확인 (게임 진행이 필요): 레벨 업/카드 브레이크 아틀라스, 슬라이트 도움말, 미니게임, 모그리 숍, 세이브 화면, 방 합성, 카드 목록 이름 폭.
     게임 조작 메모: 결정/공격 = 마우스 왼쪽·Enter, 점프 Space, 회피 마우스 오른쪽, 덱 Shift/R, 리로드 = Enter 길게, 록온 E, 적 카드 N, 메뉴 M.
     Panacea 로그: 게임 폴더 panacea_settings.txt 에 show_console=true, debug_log=true 를 잠시 넣으면 콘솔 창에 요청 경로가 나온다 (끝나면 원래대로).
     - 2026-11-09 시도: 새 빌드(667 파일)를 개발 Panacea 경로 `D:\Projects\openkh\mod\recom` 에 배치함 (이전 빈 PoC 폴더는 `mod_backup_recom_poc_20261104`). 그러나 이 세션의 셸이 **세션 0(서비스)** 에서 돌아 데스크톱 창을 보지 못함 (`recom_gamectl.py windows` 결과 없음). `launch` 가 Steam 을 세션 0 에 띄우기만 하고 게임 창은 뜨지 않음. 게임 확인은 셸이 사용자 세션(1)에서 돌 때만 가능.
   - 2026-11-09: 설치 프로그램 자기 업데이트 추가 (`installer/selfupdate.py`, kh1/docs/work-history.md 6-90). 릴리스는 태그 `v0.5.0` + 자산 `KoreanHearts-0.5.0.zip` 이름 그대로.
   - 그다음: 사용자가 원하면 커밋·배포 (build_release.ps1).
   - 설치기 연동 (BUILDERS["recom"], ready=True, spec TITLE_DIRS) -> 마지막에 게임 확인 1회 (묶어서).

1. (참고) 번역 이어 하기 방법:
   ```
   set RECOMKO_DATA=D:\Projects\openkh\data\Recom
   python -I -X utf8 recom/tools/recom_tr.py stats
   python -I -X utf8 recom/tools/recom_tr.py next 120 remastered/FORM > recom/translation/work/next.txt
   (번역을 recom/translation/work/bNNN_<이름>.txt 에 "key | 번역" 으로)
   python -I -X utf8 recom/tools/recom_tr.py apply recom/translation/work/bNNN_<이름>.txt
   ```
   WORLD 는 파일·순서대로 읽어야 화자가 보인다 (같은 문장은 키 하나라 idx 가 띄엄띄엄):
   `awk -F'\t' 'NR>1 && $2 ~ /WORLD/ && $6=="" {split($2,a,"/"); print a[2]"/"a[3]"/"a[5]"\t"$3"\t"$1"\t"$5}' recom/translation/recom_ctd.tsv | sort -t$'\t' -k1,1 -k2,2n`
   월드 폴더: 00 망각의 성(ca), 01 트래버스(tr), 02 아그라바(ag), 03 올림푸스(ol), 04 원더랜드, 05 몬스트로(mo), 06 할로윈(ha), 07 아틀란티카(at), 08 네버랜드, 09 홀로우 바스티온(ho), 10 100 에이커, 11 트와일라잇(tw), 12 데스티니(de), 13 망각의 성(ca13).
   전체 표 `recom/translation/recom_ctd.tsv` 가 번역의 현재 상태다 (apply 가 바로 씀). 작업 파일 bNNN 도 남아 있으니 표가 깨지면 다시 apply 하면 된다.
   묶음마다 `recom_table.py strip` (저장소 표 갱신), 몇 묶음마다 `recom_build.py --apply` + `recom_verify.py` (문제 0).
2. 번역 원칙: kh1-lessons.md 2절 + 용어 [terminology.md](terminology.md) (Re:COM 고유 용어는 정하면서 추가).
3. **용량 위험 (2026-11-05):** 2,188줄에서 한글 889자 (KH1 전체 번역은 1,094자). 1순위 대책: 번역을 다 끝낸 뒤 963 을 넘으면 1-2번만 쓰인 드문 글자가 든 줄을 흔한 글자로 고쳐 쓴다 (오프라인으로 끝남). 그래도 모자라면 아래 exe 분석. 처음 기록: FORM 918줄에서 한글 765자. WORLD 대사까지 하면 sysfont 963 을 넘을 가능성이 높다 -> `recom_build.py` 가 멈추면: exe 에서 글꼴 텍스처 크기(페이지 = 텍스처/칸, 0x25C2DB 의 +0x120/+0x122 를 어디서 채우는지)를 찾아 페이지를 늘릴 수 있는지 분석. 아니면 evtfont 전용 텍스트(지미니 메모·카드 화면)를 분리 배정. known-issues 2.
4. 번역이 끝나면: 한글 종류 수 <= 963 확인 (stats), 시뮬레이터로 넓은 줄 검토, 마지막에 게임 확인 1회 (묶어서: New Game 화면, 메뉴, 첫 대사, "아니요" 버튼 폭).
