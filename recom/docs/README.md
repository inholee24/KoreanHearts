# Re:COM 한글화 문서

대상: KINGDOM HEARTS Re:Chain of Memories, Steam PC판 HD 1.5+2.5 ReMIX.

## 기준 경로

```text
D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\
    KINGDOM HEARTS Re_Chain of Memories.exe     실행 파일
    Image\dt\Recom.pkg / Recom.hed              게임 데이터
D:\Projects\openkh\data\Recom                   추출 원본 (읽기 전용 기준, OpenKH ModsManager 가 추출)
D:\Projects\openkh\data\Recom\remastered        HD 판 리소스 (언어별 .ctdl, 글꼴 png/binl 등)
D:\Projects\recom-korean                        KoreanHearts 저장소의 recom 브랜치 worktree (이 저장소)
```

저장소 구조: `kh1/`(KH1), `recom/`(Re:COM), `installer/`(공용 설치기). 도구는 `recom/tools/`, 번역 표는 `recom/translation/src/` 에 둔다.

## 문서 목록

- [project-context.md](project-context.md) — 목적, 현재 단계, 다음 단계
- [file-formats.md](file-formats.md) — CTD, 글꼴(FFMW) 등 파일 포맷
- [work-history.md](work-history.md) — 작업·실험 이력
- [known-issues.md](known-issues.md) — 미확인 항목과 해결된 항목
- [kh1-lessons.md](kh1-lessons.md) — **KH1 에서 가져온 번역 규칙·작업 방식·교훈 (작업 전에 먼저 읽는다)**
- [conversation-lessons.md](conversation-lessons.md) — **대화 기록에서 배운 사용자 결정의 근거(원문)와 하지 말아야 할 시행착오 (작업 전에 먼저 읽는다)**
- [methodology-mapping.md](methodology-mapping.md) — KH1 한글화 방법론의 단계별 Re:COM 적용 검토 (그대로 / 바꿔서 / 필요 없음 / 분석 필요)
- [terminology.md](terminology.md) — Re:COM 고유 용어 (시리즈 공통 용어는 KH1 용어집)
- 번역 원칙: [../../kh1/docs/translation-rules.md](../../kh1/docs/translation-rules.md) (KH1 과 같음)

## 기록 규칙

- `확정` / `추론` / `미확인`을 섞지 않는다.
- 게임 실행 결과는 성공·실패와 무관하게 [work-history.md](work-history.md)에 기록한다.
- 재사용할 스크립트는 세션 임시 폴더가 아니라 `recom/tools/`에 둔다 (KH1 에서 임시 폴더 스크립트를 잃은 적이 있음).
- KH1 의 기법·교훈은 [../../kh1/docs](../../kh1/docs) 에 있다. 같은 문제를 다시 조사하기 전에 먼저 찾아본다.
- **도구 모듈 이름은 KH1 도구와 겹치지 않게 한다** (예: `recom_ctd.py`). 설치기가 두 타이틀의 도구를 한 실행 파일에 최상위 모듈로 묶기 때문이다 (`kh1/tools/ctd.py` 가 이미 있다).
