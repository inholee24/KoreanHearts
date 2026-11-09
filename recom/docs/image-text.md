# Re:COM 그림 속 글자 (UK 전용 .imz) 목록 — 2026-11-06

형식 (file-formats.md "IMGZ"): `IMGZ` 컨테이너 + `IMGD` 그림 n 장. 257 장 전부 형식 19 = 비압축 RGBA 32bpp, 선형 배열, 알파 0~128 (PS2 식).
UK 전용 파일 155 개, 그림 257 장, 내용이 같은 것 빼면 **208 장**. 썸네일: `recom/translation/build/imz_sheets/sheetNN.png` (번호 = list.tsv 첫 열, 저장소 제외).

## 종류별

| 묶음 | 고유 장 | 내용 | 글자 양 | 비고 |
|---|---|---|---|---|
| help_stock | 100 | 슬라이트 도움말 화면 (이름, 설명 1~3줄, "Activation", 조합, "Example", "TIPS") | 많음 (장마다 문장) | CTD 에 같은 문장 없음 -> 그림에만 있다. 조합 칸의 카드 이름(Fire, Donald ...)도 그림 |
| gamehelp | 11 | 100 에이커 미니게임 규칙 화면 (VEGGIE PANIC 등 제목, 규칙 1~3줄, TIPS) | 중간 | |
| title | 15 | 타이틀 메뉴 (NEW GAME / LOAD / THEATER / BACK, GAME SETTINGS 버튼, 저작권 글), 로고 | 적음 | 로고(KINGDOM HEARTS, Re:Chain of Memories, Reverse/Rebirth)는 KH1 처럼 원문 유지 후보 |
| 메뉴·전투 UI | 약 25 | LEVEL UP!, CARD BREAK, PAUSE, CARD OBTAINED!, SELECT WORLD, ROOM SYNTHESIS, SAVE/LOAD, MOOGLE SHOP, JOURNAL, D REPORT, CARD DUEL! 등 장식 글꼴 제목·작은 라벨 | 적음~중간 | KH1 11-01 에 한 방식 (제목 다시 그리기) |
| 미니게임 HUD | 6 | START/READY/CLEAR/EXCELLENT/FAILED, NEW RECORD, MONSTRO TIME | 적음 | |
| save 월드 로고 | 1 (14 로고) | 월드 이름 로고 (WONDERLAND, AGRABAH ...) | 로고 | 원문 유지 후보 |
| end_* | 7 | 엔딩 "The End" + 일러스트 | 1 단어 | 원문 유지 후보 |
| card | 24 | 카드 그림 (무기·인물·적 초상, 아이콘). 글자는 숫자뿐 | 없음 | 바꿀 것 없음 |
| wselect / wwarp 월드 그림 | 15 | 월드 그림. wselect#0 에 SELECT WORLD / WORLD CARD | 첫 장만 | |
| gauge 등 | 5 | 소라·리쿠 얼굴, 숫자, HP/MAX/D-POINT | 거의 없음 | |

## 결정 (2026-11-06 사용자): 전부 한글화 (도움말 포함), 로고는 원문 유지

진행: **완료.** help_stock 100 장 (`recom_helpstock.py apply`, 명세 src/helpstock.tsv) + 나머지 39 장 (`recom_imgtext.py apply`, 명세 src/imgtext.json). 원문 유지 목록은 work-history 2026-11-06.

게임 확인 (2026-11-09) 뒤 추가 규칙:
- 타이틀·camp 는 PC 판이 같은 폴더 `UK_<이름>_{other,ps,xbox}.png` 를 그린다 -> `recom_imgtext` 가 짝 PNG 에도 같은 작업 (file-formats.md).
- 글자는 `.lad` 스프라이트 사각형 안에 있어야 한다 (게임이 사각형만 잘라 그림). 작업의 `box` = 그 사각형, `recom_ladbox.py apply` 로 채움. 칸으로 나뉜 제목(PAUSE)은 칸마다 한 글자.
- 타이틀 선택 줄의 테두리 글자는 `ring_of` (앞 작업 글자 모양 + 4px 고리).
- 40px 안팎의 작은 한글에 `bold`(외곽선)를 더하지 않는다: ㄹ·ㅌ 처럼 가로획이 많은 글자의 틈이 메워진다 (2026-11-10 타이틀 "로드"). 같은 메뉴의 줄은 `sz` 로 크기를 통일.

## (이전) 결정 필요

KH1 때처럼 "바꿀 것 / 둘 것" 을 정해야 한다. 특히 help_stock 100 장은 문단을 그림에 다시 그리는 큰 작업이다.
