"""이미지 속 글자 한글화 (48차~).

  python tools/imgtext.py [묶음 ...]            확인용 미리보기만 (scratchpad 아님: translation/build/imgtext_preview/)
  python tools/imgtext.py --apply [묶음 ...]    mod/kh1 에 쓴다

원본: data/kh1/<rel> (UK_ 영어판 파일). DDS 는 모두 비압축 32bpp, 채널 마스크 R=0xFF0000 -> 바이트 순서 BGRA (48차 확인).
HD 교체는 파일 단위라 그림 크기를 바꿔도 된다 (sysfont 1024 -> 2048, docs/exe-analysis.md).

작업 = JOBS[묶음] 의 (rel, [동작...]):
  ("erase", (x0, y0, x1, y1))                       상자 안을 투명으로
  ("erasecol", (x0, y0, x1, y1), (r, g, b), tol)     상자 안에서 이 색 (각 채널 차 tol 이하) 화소만 투명으로
  ("fill", (x0, y0, x1, y1), (r, g, b, a))          상자를 한 색으로
  ("copy", (sx0, sy0, sx1, sy1), (dx, dy))          같은 그림의 다른 곳을 복사 (배경 메우기)
  ("canvas", (w, h))                                 그림을 이 크기의 투명 그림으로 바꿈 (영어판이 1x1 빈 그림인 경우)
  ("paste", 다른rel, (x0, y0, x1, y1))              다른 원본 파일의 같은 자리를 붙여 넣음 (일본판 공용 파일의 부제 줄 등)
  ("scaled", 다른rel, 상자, (dx, dy))               다른 작업 결과 (같은 실행에서 만든 것) 의 상자를 크기 비율대로 줄여 붙임
  ("retext", (x0, y0, x1, y1), 글, 옵션)             불투명 배경 위 글자: 상자 안에서 배경(중간값 필터)과 다른 화소를 글자로 보고
                                                    주변 배경으로 메운 뒤 (정규화 블러), 같은 색으로 한글을 쓴다.
                                                    옵션: align ('l','c','r'), h (기본 상자 높이의 0.62), thr (기본 36), color (기본 자동),
                                                    dark (True 면 밝은 바탕의 어두운 글자)
  ("relabel", (x0, y0, x1, y1), 글, 옵션)            투명 바탕 위 단색/그라데이션 글자 (메뉴 색 테마 그림): 상자 안 원래 글자의 줄마다 평균 색을
                                                    새 글자에 그대로 입힌다 (세로 그라데이션 유지). 옵션은 text 와 같음 + align
  ("restyle", (x0, y0, x1, y1), 글, 옵션)            장식 글씨 (채움 + 테두리 + 번짐). 상자 좌우 끝 m px 를 줄마다 바탕으로 보고, 바탕과 다른 화소를
                                                    글자로 본다. 채움 = 글자 안쪽 줄별 중간값, 테두리 = 가장자리 중간값, 번짐 = 반투명 화소.
                                                    지운 자리는 줄별 바탕색. 옵션: thr, m, ow (테두리 px), glow (번짐 반지름), h, w, shear, track, align, font
  ("vfill", (x0, y0, x1, y1), ys)                   상자 안 각 열을 그 열의 y=ys 화소로 채움 (세로로 고른 그라데이션 배경 메우기)
  ("text", 글, (x, y), 옵션)                         글 상자 왼쪽 위 기준. 옵션: size, color, font, h (글자 높이 px 로 크기 맞춤),
                                                    w (최대 폭, 넘으면 가로로 줄임), align ('l','c','r', x 가 각 기준), track (자간),
                                                    stroke (테두리 px), stroke_color, shear (기울기, 0.2 = 오른쪽으로 20%)
"""
import os, struct, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageMath

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "kh1")
MOD = os.path.join(ROOT, "mod", "kh1")
PREVIEW = os.path.join(ROOT, "translation", "build", "imgtext_preview")
FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_REG = r"C:\Windows\Fonts\malgun.ttf"

TITLE = "remastered/title/title.img/"
EV = "remastered/eveffect/"
GRAY = (129, 128, 129, 255)       # 일본판 부제 글자색 (공용 파일에서 잰 값)


def _wt(text, x, y, h, **o):
    return ("text", text, (x, y), dict(dict(h=h, color=GRAY, font=FONT_REG), **o))


def _world(d, off, ops):
    """영어판 UK_ 파일 (부제 없음) 을 바탕으로 일본판 공용 파일 -off.dds 의 줄표를 붙이고 한글 부제를 쓴다."""
    jp = f"{EV}{d}/-{off}.dds"
    uk = f"{EV}{d}/UK_{d.split('/')[1].replace('.', '_')}{off}.dds"
    return (uk, [("paste", jp, b) if isinstance(b[0], int) else b for b in ops])


def _world_jp(d, off, ops):
    """영어판이 1x1 빈 그림인 경우: 일본판 공용 파일 (부제만 든 256x128) 을 바탕으로 가나를 지우고 한글을 쓴다.
    두 줄로 잘린 조각을 게임이 이어 붙인다 (일본판 글자 배치에서 추론): 이어지는 순서대로 조각 자리에 나눠 쓴다."""
    jp = f"{EV}{d}/-{off}.dds"
    uk = f"{EV}{d}/UK_{d.split('/')[1].replace('.', '_')}{off}.dds"
    return (uk, [("canvas", (256, 128)), ("paste", jp, (0, 0, 256, 128))] + ops)



L, C, R = dict(align="l"), dict(align="c"), dict(align="r")
DARK = dict(align="c", dark=True)
GH_COMMON = [((246, 42, 420, 80), "구미 가이드", L), ((906, 26, 1140, 62), "구미 차고로", L),
             ((906, 73, 1130, 110), "가이드 열기/닫기", L),
             ((864, 173, 1049, 213), "셀렉트", R), ((976, 348, 1049, 389), "빌드", R), ((942, 525, 1049, 565), "인스펙트", R)]
_ROT_G, _ROT_GRID = ((284, 698, 474, 738), "구미 회전", L), ((862, 698, 1022, 738), "그리드 회전", R)
_UP, _DOWN = ((294, 301, 336, 342), "위", L), ((294, 355, 368, 395), "아래", L)
_REMODEL, _ENTIRE = ((184, 173, 460, 212), "구미 쉽 개조", C), ((502, 173, 746, 212), "쉽 전체 선택", C)
_PAINT, _PALETTE = ((186, 173, 322, 212), "페인트", C), ((362, 173, 544, 212), "컬러 팔레트", C)
_BUILD_TAB, _SEL_TAB = ((186, 110, 258, 148), "빌드", L), ((186, 110, 370, 148), "셀렉트", L)
_HOLD = ((624, 525, 914, 565), "누르고 있으면 구미 조정", L)
_MOVE_CUR = ((204, 555, 380, 592), "커서 이동", C)
GH_PAGES = [
    ("0", [((186, 110, 292, 148), "인스펙트", L), ((188, 240, 378, 277), "카메라 줌", DARK),
           ((298, 301, 332, 342), "확대", L), ((298, 355, 352, 395), "축소", L),
           ((624, 260, 844, 301), "조작 표시", L), ((624, 348, 824, 389), "리포트 표시", L), ((624, 436, 694, 477), "빌드", L),
           ((624, 525, 834, 565), "장비 테스트", L), ((768, 698, 1022, 738), "구미 쉽 회전", R)]),
    ("11d80", [_BUILD_TAB, _REMODEL, _ENTIRE, ((252, 240, 316, 277), "그리드", DARK), _UP, _DOWN,
               ((624, 260, 866, 301), "쉽 전체 선택", L), ((624, 348, 816, 389), "구미 떼기", L),
               ((624, 436, 814, 477), "구미 달기", L), _HOLD, _MOVE_CUR, _ROT_G, _ROT_GRID]),
    ("23d70", [_BUILD_TAB, _REMODEL, _ENTIRE, ((178, 240, 390, 277), "선택한 구미", DARK), _UP, _DOWN, _HOLD, _MOVE_CUR, _ROT_G]),
    ("358b0", [_BUILD_TAB, _REMODEL, _ENTIRE, ((206, 240, 360, 277), "구미 쉽", DARK), _UP, _DOWN,
               ((624, 260, 738, 301), "전체 칠하기", L), ((624, 348, 826, 389), "선택 해제", L),
               ((624, 436, 894, 477), "처음부터 만들기", L), ((224, 555, 362, 592), "쉽 이동", C),
               ((284, 698, 534, 738), "쉽 전체 회전", L), _ROT_GRID]),
    ("47d20", [_SEL_TAB, _PAINT, _PALETTE, ((624, 348, 752, 389), "페인트", L), ((624, 436, 894, 477), "구미 메뉴로 나가기", L),
               ((624, 525, 694, 565), "빌드", L), ((200, 393, 386, 430), "구미 바꾸기", C), ((208, 513, 378, 550), "분류 바꾸기", C),
               _ROT_G, _ROT_GRID]),
    ("59740", [_SEL_TAB, _PAINT, _PALETTE, ((624, 260, 804, 301), "컬러 팔레트", L), ((624, 348, 798, 389), "페인트 끝내기", L),
               ((624, 436, 798, 477), "페인트 끝내기", L), ((624, 525, 694, 565), "빌드", L),
               ((200, 393, 386, 430), "구미 바꾸기", C), ((204, 513, 380, 550), "색 바꾸기", C), _ROT_G, _ROT_GRID]),
    ("6b770", [_SEL_TAB, _PAINT, _PALETTE, ((624, 260, 804, 301), "팔레트 닫기", L), ((624, 348, 812, 389), "팔레트 초기화", L),
               ((624, 436, 804, 477), "팔레트 닫기", L), ((624, 525, 754, 565), "색 정하기", L),
               ((210, 486, 374, 522), "색 고르기", C), ((562, 643, 820, 682), "컬러 휠 회전", C)]),
]


_SL = dict(shear=0.2)
WIN_LABELS = [((5, 43, 138, 67), "메뉴", _SL), ((159, 43, 240, 67), "스톡", {}),
              ((258, 43, 330, 67), "시간", {}), ((6, 218, 101, 246), "먼니", {}),
              ((137, 218, 268, 246), "숍", _SL), ((311, 218, 409, 246), "기록", {}),
              ((283, 386, 335, 404), "합성", {}),
              ((225, 414, 376, 440), "구미", _SL), ((225, 451, 361, 473), "워크", _SL), ((225, 483, 359, 505), "숍", _SL)]

JOBS = {
    # 타이틀 메뉴 버튼: 검은 글자, 영문 대문자 높이 26 (y 18~43), x 76 부터. 막대 아래 줄 y 54~57 은 그대로
    "title": [
        (TITLE + "UK_title_img140.dds", [("erase", (70, 12, 700, 50)), ("text", "시어터", (76, 17), dict(h=27, track=3))]),
        (TITLE + "UK_title_img174670.dds", [("erase", (70, 12, 700, 50)), ("text", "새 게임", (76, 17), dict(h=27, track=3))]),
        (TITLE + "UK_title_img17ab30.dds", [("erase", (70, 12, 700, 50)), ("text", "불러오기", (76, 17), dict(h=27, track=3))]),
        (TITLE + "UK_title_img180ff0.dds", [("erase", (70, 12, 700, 50)), ("text", "돌아가기", (76, 17), dict(h=27, track=3))]),
    ] + [
        # 오른쪽 아래 "[Esc/버튼] GAME SETTINGS" 막대: 글자 x 775~977, y 89~103, 색 약 (20,20,20). 배경은 가로 그라데이션
        (TITLE + f"UK_title_img{n}.png", [("vfill", (770, 86, 990, 106), 108),
                                         ("text", "게임 설정", (776, 89), dict(h=15, track=1, color=(20, 20, 20, 255)))])
        for n in ("1766f0", "_other", "_ps", "_xbox")
    ],
    # 전투 명령 메뉴 제목 (48차): 회색 (128,128,128) 기울어진 굵은 글씨, 낱말마다 따로 붙인 스프라이트로 추정.
    # 원래 글자 상자 안에서만 바꾼다. 조각을 이어 붙이는 LOCK ON!, Danger!, munnies, Tech 와 버튼 글자는 그대로.
    "command": [
        ("remastered/command2/uitex.bin/UK_uitex_bin20c0.png",
         [op for (x0, y0, x1, y1, t) in [(6, 4, 154, 20, "커맨드"), (5, 26, 96, 42, "마법"), (107, 26, 227, 42, "소환"),
                                         (6, 48, 163, 65, "레벨 업!"), (5, 70, 82, 86, "아이템"), (5, 91, 103, 109, "파티"),
                                         (8, 113, 156, 130, "숏컷")]
          for op in (("erase", (x0, y0, x1 + 1, y1 + 1)),
                     ("text", t, (x0, y0), dict(h=y1 - y0, w=x1 - x0, color=(128, 128, 128, 255), shear=0.2)))]),
        # exchange 쪽 128x128 은 같은 배치의 절반 크기 (줄 경계가 정확히 절반) -> 위 결과를 줄여서 쓴다
        ("exchange/UK_uitex_bin20c0.png", [("erase", (0, 0, 128, 66)),
                                            ("scaled", "remastered/command2/uitex.bin/UK_uitex_bin20c0.png", (0, 0, 256, 132), (0, 0))]),
    ],
    # 구미 가이드 도움말 7장 (48차): 1304x1024 불투명 그림. retext 로 배경을 메우고 같은 색으로 다시 쓴다.
    # 용어는 구미 대사 번역과 같게 (빌드/셀렉트/인스펙트 모드, 컬러 팔레트, 구미 차고)
    "ghelp": [(f"remastered/gumi/ghelp.bin/UK_ghelp_bin{n}.png", [("retext",) + r for r in GH_COMMON + rows])
              for n, rows in GH_PAGES],
    # 메뉴 공용 그림 win.dat (48차): 색 테마 16종 x (일반, _deck) + 0 의 버튼 변형 3종. 글자는 투명 바탕의 기울어진 굵은 글씨.
    # LV/HP/MP, NEW, 버튼·키 그림은 그대로
    "windat": [(f"remastered/menu/win.dat/UK_win_dat{v}.png", [("relabel",) + r + ("remastered/menu/win.dat/UK_win_dat0.png",) for r in WIN_LABELS])
               for v in ["0", "0_other", "0_ps", "0_xbox"] + [f"{c}{d}" for c in "123456789cdef" for d in ("", "_deck")]],
    # 설정 메뉴 그림 (48차): 위 "GAME SETTINGS" 막대 (노란 막대 위 검은 기울어진 글씨), 일시 정지 "PAUSE" (회색, 투명 바탕)
    "settingimg": [
        ("SM:uk/l2d/setting_1525.l2d#1", [("fill", (110, 646, 516, 680), (188, 136, 1, 255)),
                                          ("text", "게임 설정", (114, 649), dict(h=25, shear=0.25, track=4, color=(3, 2, 0, 255)))]),
        ("SM:uk/l2d/pause.l2d#0", [("erase", (494, 82, 790, 121)), ("erasecol", (790, 82, 830, 121), (128, 128, 128), 6),
                                   ("text", "일시 정지", (500, 84), dict(h=33, shear=0.25, track=14, color=(128, 128, 128, 255)))]),
    ],
    # 구미 미션 화면 (48차): 장식 글씨. 숫자, "or", 버튼은 그대로
    "gummimission": [
        ("remastered/worldmap/quesys.tzb/UK_quesys_tzb80.dds",
         [("restyle", (176, 44 + d, 296, 73 + d), "미션", dict(ow=2, h=18)) for d in (0, 186, 374)]
         + [("restyle", (412, 44 + d, 512, 75 + d), "레벨", dict(ow=2, h=19)) for d in (0, 186, 374)]
         + [("restyle", (32, 624, 152, 652), "미션", dict(ow=2, h=18)), ("restyle", (264, 622, 368, 654), "레벨", dict(ow=2, h=19, clear=True)),
            ("restyle", (2, 852, 512, 910), "구미 쉽 미션", dict(ow=3, glow=3, h=38, shear=0.2, clear=True))]),
        ("remastered/worldmap/quesys.tzb/UK_quesys_tzb20380.dds",
         [("restyle", (0, 610, 140, 652), "완료!", dict(ow=3, glow=2, h=26, shear=0.2, clear=True, fill=(245, 245, 200, 255),
                                                       ol=(120, 100, 20, 255), glow_color=(210, 190, 40, 255))),
          ("restyle", (4, 688, 236, 720), "종합 점수", dict(ow=2, h=19, clear=True, fill=(230, 135, 150, 255), ol=(80, 48, 48, 255))),
          ("restyle", (64, 720, 244, 752), "최고 점수", dict(ow=1, h=19, clear=True, fill=(60, 240, 240, 255), ol=(20, 50, 80, 255))),
          ("restyle", (0, 754, 126, 788), "합계", dict(ow=3, h=23, shear=0.2, clear=True)),
          ("restyle", (156, 754, 290, 788), "점수", dict(ow=3, h=23, shear=0.2, clear=True, fill=(110, 245, 170, 255), ol=(10, 115, 130, 255))),
          ("restyle", (0, 786, 218, 820), "최고 점수", dict(ow=3, h=23, shear=0.2, clear=True)),
          ("restyle", (218, 785, 356, 814), "게임 모드", dict(ow=1, h=18, clear=True, fill=(245, 180, 20, 255), ol=(90, 50, 0, 255)))]),
        ("remastered/worldmap/gm_help.tzb/UK_gm_help_tzb80.png",
         [("restyle", (66, 112, 352, 154), "미션 규칙", dict(ow=3, h=26, shear=0.2)),
          ("restyle", (806, 114, 950, 152), "점수", dict(ow=3, h=24, shear=0.2)),
          ("restyle", (796, 486, 960, 526), "회복", dict(ow=3, h=24, shear=0.2)),
          ("restyle", (56, 458, 194, 494), "출발", dict(ow=2, h=24, shear=0.2, fill=(206, 206, 206, 255), ol=(60, 60, 60, 255))),
          ("restyle", (532, 458, 674, 494), "도착", dict(ow=2, h=24, shear=0.2, thr=70))]),
        ("remastered/worldmap/gm_ending.tzb/UK_gm_ending_tzb33880.png",
         [("restyle", (4, 0, 960, 92), "축하합니다!", dict(ow=2, glow=6, h=66, shear=0.25, track=6, clear=True, clearbox=(0, 0, 1024, 90),
                                                           fill=(250, 250, 250, 255), ol=(230, 205, 50, 255), glow_color=(230, 205, 50, 255))),
          ("restyle", (290, 86, 670, 124), "- 미션 완료 -", dict(ow=1, glow=3, h=22, shear=0.2, clear=True, clearbox=(280, 86, 680, 128),
                                                              fill=(250, 250, 250, 255), ol=(230, 205, 50, 255), glow_color=(230, 205, 50, 255))),
          ("erase", (0, 86, 282, 102)), ("erase", (678, 86, 1024, 102))]),
        ("remastered/worldmap/wexsys.tzb/UK_wexsys_tzb80.dds",
         [("restyle", (636, 6, 892, 70), "점수", dict(ow=4, glow=3, h=40, shear=0.25, clear=True, fill=(110, 245, 170, 255),
                                                       ol=(10, 115, 130, 255), glow_color=(10, 115, 130, 255))),
          ("restyle", (28, 82, 712, 148), "최고 기록 갱신", dict(ow=5, h=38, shear=0.25)),
          ("restyle", (28, 212, 712, 278), "미션 완료", dict(ow=5, h=38, shear=0.25))]),
    ],
    # 월드 제목 (48차): 일본판은 영어 로고 + 가나 부제, 영어판은 부제를 지운 그림 (또는 1x1). 부제 자리에 한글 이름.
    # 좌표 = 일본판 공용 파일에서 잰 가나·줄표 상자 (docs/work-history 6-76)
    "world": [
        _world("al/al_000.dpx", "1c370", [(43, 456, 131, 503), (386, 456, 474, 503), _wt("아그라바", 256, 461, 34, align="c", w=205)]),
        _world("ew/ew_000.dpx", "1dd0", [(19, 474, 111, 488), _wt("엔드 오브 더 월드", 16, 398, 34, w=477)]),
        _world("pc/pc_000.dpx", "26ad0", [(19, 458, 111, 504), _wt("홀로우 바스티온", 135, 463, 34, w=370)]),
        _world("po/po_001.dpx", "1c80", [(2, 458, 94, 505), _wt("100 에이커의 숲", 123, 462, 34, w=364)]),
        _world("pp/pp_000.dpx", "137f0", [(23, 458, 115, 503), (399, 458, 491, 503),
                                          _wt("네버랜드", 255, 462, 34, align="c", w=240, color=(222, 118, 18, 255))]),
        _world("nm/nm_000.dpx", "158a0", [(17, 460, 109, 503), _wt("할로윈 타운", 152, 464, 34, w=325)]),
        _world("lm/lm_002.dpx", "12a40", [(19, 95, 111, 142), _wt("아틀란티카", 134, 99, 34, w=273)]),
        # 부제 칸이 세로이고 게임이 반시계로 90도 돌려 가로로 보인다 (일본판 가나도 시계 방향으로 누워 있음, 57차) -> 글자도 시계 방향으로 돌려 쓴다
        _world("di/di_002.dpx", "22c00", [_wt(c, 480, 36 + k * 49, 32, align="c", rot=90) for k, c in enumerate("데스티니 아일랜드") if c != " "]),
        _world("pi/pi_000.dpx", "e410", [(194, 88, 260, 111), (444, 88, 510, 111),
                                         _wt("몬스트로", 352, 90, 17, align="c", w=154, color=(129, 87, 198, 255))]),
        _world_jp("aw/aw_001.dpx", "21280", [("erase", (125, 70, 256, 122)), ("erase", (0, 8, 165, 58)),
                                             _wt("원더랜", 132, 78, 34, w=121), _wt("드", 4, 16, 34)]),
        _world_jp("he/he_000.dpx", "129e0", [("erase", (86, 8, 256, 58)), ("erase", (0, 70, 256, 122)),
                                             _wt("올림푸스 콜", 7, 77, 34, w=242), _wt("로세움", 91, 16, 34, w=160)]),
        _world_jp("tw/tw_000.dpx", "21380", [("erase", (128, 6, 256, 58)), ("erase", (0, 72, 256, 122)),
                                             _wt("트래버", 135, 14, 34, w=114), _wt("스 타운", 9, 80, 34, w=238)]),
        _world_jp("tz/tz_000.dpx", "33ae0", [("erase", (0, 5, 256, 58)), ("erase", (128, 70, 256, 122)),
                                             _wt("딥", 136, 78, 34), _wt("정글", 20, 13, 34)]),
    ],
    # 구미 로고 (49차): 월드맵 아래 "GUMMI GARAGE"/"GUMMI SHIP MISSION" (wdata), 구미 차고 위 제목 (gumi_tex),
    # "GUMMI SHIP" 아이콘 (gumi_tex 21400, command2 16c40 = 같은 그림 +10,+10): 반투명 갈색 집 모양 위 글자.
    # 글자 줄은 그림의 세로로 곧은 구간에 있으므로 위/아래 깨끗한 줄을 복사해 지우고, 몸통 밖 그림자 점을 지운 뒤 다시 쓴다.
    # 색은 원본에서 잰 값 (채움/테두리·번짐)
    "gummilogo": [
        ("remastered/worldmap/wdata.bin/UK_wdata_bin1000.dds",
         [("restyle", (0, 0, 292, 50), "구미 차고", dict(ow=1, glow=3, shear=0.2, track=4, align="l", clear=True, clearbox=(0, 0, 512, 64),
                                                         fill=(88, 143, 190, 255), ol=(47, 25, 255, 255), glow_color=(47, 25, 255, 255)))]),
        ("remastered/worldmap/wdata.bin/UK_wdata_bin4000.dds",
         [("restyle", (0, 0, 386, 52), "구미 쉽 미션", dict(ow=1, glow=3, shear=0.2, track=4, align="l", clear=True, clearbox=(0, 0, 512, 64),
                                                            fill=(245, 224, 86, 255), ol=(255, 182, 25, 255), glow_color=(255, 182, 25, 255)))]),
        ("remastered/gumi/gumi_tex.bin/UK_gumi_tex_bin22c00.dds",
         [("restyle", (0, 0, 386, 42), "구미 차고", dict(ow=3, shear=0.3, track=10, align="l", clear=True, clearbox=(0, 0, 512, 64),
                                                         fill=(112, 183, 245, 255), ol=(16, 0, 255, 255)))]),
        ("remastered/gumi/gumi_tex.bin/UK_gumi_tex_bin24000.dds",
         [("restyle", (0, 0, 194, 27), "구미 쉽 미션", dict(ow=1, glow=1, shear=0.2, track=2, align="l", clear=True, clearbox=(0, 0, 256, 32),
                                                            fill=(245, 224, 86, 255), ol=(255, 182, 25, 255), glow_color=(255, 182, 25, 255)))]),
        ("remastered/gumi/gumi_tex.bin/UK_gumi_tex_bin21400.dds",
         [("vfill", (0, 41, 128, 52), 40), ("erase", (0, 52, 29, 53)), ("erase", (85, 52, 128, 53)), ("vfill", (0, 61, 128, 73), 76),
          ("text", "구미", (56, 42), dict(C, h=10, track=4, color=(254, 162, 103, 255))),
          ("text", "쉽", (56, 62), dict(C, h=10, color=(254, 162, 103, 255)))]),
        ("remastered/command2/uitex.bin/UK_uitex_bin16c40.dds",
         [("vfill", (0, 51, 128, 62), 50), ("erase", (0, 62, 39, 63)), ("erase", (95, 62, 128, 63)), ("vfill", (0, 71, 128, 83), 86),
          ("text", "구미", (66, 52), dict(C, h=10, track=4, color=(254, 162, 103, 255))),
          ("text", "쉽", (66, 72), dict(C, h=10, color=(254, 162, 103, 255)))]),
    ],
}


# 비압축 BGRA DDS 헤더 견본 (영어판 UK_title_img174670.dds 와 같은 형식). 크기·pitch 는 save 가 채운다
BGRA_HDR = None
DONE = {}
_SM_STARTED = {}                   # 이번 실행에서 이미 쓴 l2d (같은 파일의 여러 그림을 차례로 고칠 때 앞 결과 유지)                          # 이번 실행에서 만든 결과 (rel -> 그림), "scaled" 가 쓴다


def _bgra_hdr():
    return open(os.path.join(DATA, TITLE + "UK_title_img174670.dds"), "rb").read()[:128]


# 설정 메뉴 (Image/SettingMenu.pkg) 레이아웃 l2d 안의 TIM2 그림: rel = "SM:uk/l2d/<파일>#<TIM2 순번>"
# TIM2 1장 1그림, 32bpp RGBA (알파 0~128 = PS2 식 또는 0~255 그대로). 같은 크기로 제자리에 다시 쓴다 -> mod/kh1/uk/l2d/
SM_SRC = os.path.join(ROOT, "data", "settingmenu")


def _tim_at(b, k):
    import re
    o = [m.start() for m in re.finditer(b"TIM2", b)][k]
    p = o + 16
    tot, cl, isz, hs, cc, fmt, mip, ct, it, w, h = struct.unpack_from("<IIIHHBBBBHH", b, p)
    if it != 3:
        sys.exit("TIM2 32bpp 아님")
    return p + hs, w, h


def _sm(rel):
    f, k = rel[3:].split("#")
    return f, int(k)


def load(path):
    rel = os.path.relpath(path, DATA).replace(os.sep, "/")
    if rel.startswith("SM:"):
        f, k = _sm(rel)
        b = open(os.path.join(SM_SRC, f), "rb").read()
        o, w, h = _tim_at(b, k)
        img = Image.frombytes("RGBA", (w, h), b[o:o + w * h * 4])
        half = img.split()[3].getextrema()[1] <= 128
        if half:
            img.putalpha(img.split()[3].point(lambda v: min(255, v * 2)))
        return ("SM", half), img
    return _load(path)


def _load(path):
    if path.lower().endswith(".dds"):
        b = open(path, "rb").read()
        h, w = struct.unpack_from("<II", b, 12)
        if b[84:88] in (b"DXT1", b"DXT3", b"DXT5"):      # 일본판 공용 파일 (월드 제목 등): 읽기만, 쓰기는 비압축 BGRA
            return BGRA_HDR, Image.open(path).convert("RGBA")
        if b[84:88] != bytes(4) or struct.unpack_from("<IIIII", b, 88) != (32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000):
            sys.exit(f"{path}: BGRA 32bpp 비압축 DDS 가 아님")
        return b[:128], Image.frombytes("RGBA", (w, h), b[128:128 + w * h * 4], "raw", "BGRA")
    return None, Image.open(path).convert("RGBA")


def save(path, hdr, img):
    if isinstance(hdr, tuple) and hdr[0] == "SM":
        rel = os.path.relpath(path, MOD).replace(os.sep, "/")
        f, k = _sm(rel)
        out = os.path.join(MOD, f)
        src = out if os.path.exists(out) and _SM_STARTED.get(f) else os.path.join(SM_SRC, f)
        b = bytearray(open(src, "rb").read())
        o, w, h = _tim_at(b, k)
        if hdr[1]:
            img = img.copy()
            img.putalpha(img.split()[3].point(lambda v: (v + 1) // 2))
        b[o:o + w * h * 4] = img.tobytes()
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(bytes(b))
        _SM_STARTED[f] = True
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if hdr is None:
        img.save(path)
        return
    w, h = img.size
    hdr = bytearray(hdr)
    struct.pack_into("<II", hdr, 12, h, w)
    struct.pack_into("<I", hdr, 20, w * 4)
    open(path, "wb").write(bytes(hdr) + img.tobytes("raw", "BGRA"))


def fit_font(text, o):
    path = o.get("font", FONT_BOLD)
    if "h" not in o:
        return ImageFont.truetype(path, o.get("size", 24))
    lo, hi = 6, 200
    while lo < hi:                                     # 한글 글자 높이가 h 이하인 가장 큰 크기
        mid = (lo + hi + 1) // 2
        f = ImageFont.truetype(path, mid)
        bb = f.getbbox("한")
        if bb[3] - bb[1] <= o["h"]:
            lo = mid
        else:
            hi = mid - 1
    return ImageFont.truetype(path, lo)


def render_text(text, o):
    """글을 투명 바탕 RGBA 로. 왼쪽 위 = 잉크 상자 왼쪽 위."""
    f = fit_font(text, o)
    track, sw = o.get("track", 0), o.get("stroke", 0)
    ws = [f.getlength(c) for c in text]
    W = int(sum(ws) + track * (len(text) - 1) + 4 * sw + 8)
    H = int(f.size * 1.6 + 4 * sw)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 2 * sw + 2
    for c, cw in zip(text, ws):
        d.text((x, 2 * sw), c, font=f, fill=o.get("color", (0, 0, 0, 255)),
               stroke_width=sw, stroke_fill=o.get("stroke_color", (0, 0, 0, 255)))
        x += cw + track
    if o.get("shear"):
        s = o["shear"]
        im = im.transform((W + int(H * s) + 2, H), Image.AFFINE, (1, s, -H * s, 0, 1, 0), Image.BICUBIC)
    bb = im.getbbox()
    im = im.crop(bb) if bb else im
    if "w" in o and im.width > o["w"]:
        im = im.resize((o["w"], im.height), Image.LANCZOS)
    if o.get("rot"):                                   # 시계 방향 회전 (게임이 칸을 돌려 그리는 그림)
        im = im.rotate(-o["rot"], resample=Image.BICUBIC, expand=True)
    return im


def inpaint(img, mask):
    """mask (L, 255 = 메울 곳) 를 주변 화소의 가중 평균으로 메운다. 반지름을 늘려 가며 남은 곳을 채운다."""
    rgb = img.convert("RGB")
    valid = ImageChops.invert(mask)
    out = rgb.copy()
    todo = mask
    for r in (2, 4, 8, 16, 32):
        if not todo.getbbox():
            break
        pre = Image.composite(rgb, Image.new("RGB", rgb.size), valid).filter(ImageFilter.GaussianBlur(r))
        wv = valid.filter(ImageFilter.GaussianBlur(r))
        bands = [ImageMath.lambda_eval(lambda a: (a["p"] * 255 / (a["w"] + 0.001)), p=b.convert("F"), w=wv.convert("F")).convert("L")
                 for b in pre.split()]
        fill = Image.merge("RGB", bands)
        ok = wv.point(lambda v: 255 if v > 8 else 0)
        put = ImageChops.multiply(todo, ok)
        out = Image.composite(fill, out, put)
        rgb = Image.composite(fill, rgb, put)
        valid = ImageChops.lighter(valid, put)
        todo = ImageChops.subtract(todo, put)
    res = out.convert("RGBA")
    res.putalpha(img.split()[3])
    return res


def retext(img, box, text, o):
    reg = img.crop(box).convert("RGB")
    lum = reg.convert("L")
    if o.get("dark"):          # 밝은 바탕의 어두운 글자: 주변 최댓값보다 어두운 곳
        diff = ImageChops.subtract(lum.filter(ImageFilter.MaxFilter(o.get("k", 11))), lum)
    else:                      # 어두운 바탕의 밝은 글자: 주변 최솟값보다 밝은 곳
        diff = ImageChops.subtract(lum, lum.filter(ImageFilter.MinFilter(o.get("k", 11))))
    m = diff.point(lambda v: 255 if v > o.get("thr", 14) else 0)
    # 글자색: 차이가 큰 화소들의 평균
    px = [(d, c) for d, c, mm in zip(diff.getdata(), reg.getdata(), m.getdata()) if mm]
    if "color" in o:
        col = o["color"]
    elif px:
        px.sort(key=lambda t: -t[0])
        top = [c for _, c in px[:max(1, len(px) // 3)]]
        col = tuple(sum(c[i] for c in top) // len(top) for i in range(3)) + (255,)
    else:
        col = (255, 255, 255, 255)
    m = m.filter(ImageFilter.MaxFilter(o.get("grow", 9)))
    full = Image.new("L", img.size, 0)
    full.paste(m, box[:2])
    img = inpaint(img, full)
    x0, y0, x1, y1 = box
    t = render_text(text, dict(h=o.get("h", int((y1 - y0) * 0.62)), color=col, w=o.get("w", x1 - x0 + o.get("extra", 0)),
                               font=o.get("font", FONT_BOLD), track=o.get("track", 1)))
    al = o.get("align", "l")
    x = x0 + 2 if al == "l" else (x0 + x1 - t.width) // 2 if al == "c" else x1 - t.width - 2
    y = (y0 + y1 - t.height) // 2 + o.get("dy", 0)
    img.alpha_composite(t, (int(x), int(y)))
    return img


def _median(px):
    if not px:
        return None
    return tuple(sorted(p[i] for p in px)[len(px) // 2] for i in range(4))


def relabel(img, box, text, o, ref):
    """ref = 같은 배치의 기준 그림 (win_dat0, 회색 글자·투명 바탕) -> 글자 모양 S. 변형마다 S 위 색 (채움), S 바깥 1~2px
    테두리 색, 그 밖 바탕 색을 재서 지우고 같은 방식으로 한글을 그린다 (반전 변형 6 = 검은 바탕에 뚫린 글자도 처리)."""
    x0, y0, x1, y1 = box
    pad = 4
    X0, Y0, X1, Y1 = x0 - pad, y0 - pad, x1 + pad + 1, y1 + pad + 1
    S = ref.crop((X0, Y0, X1, Y1)).split()[3].point(lambda v: 255 if v > 128 else 0)
    ring = ImageChops.subtract(S.filter(ImageFilter.MaxFilter(5)), S)
    outer = ImageChops.invert(S.filter(ImageFilter.MaxFilter(9)))
    reg = img.crop((X0, Y0, X1, Y1))
    P = list(reg.getdata()); Sd = list(S.getdata()); Rd = list(ring.getdata()); Od = list(outer.getdata())
    W = reg.width
    bgc = _median([p for p, m in zip(P, Od) if m]) or (0, 0, 0, 0)
    rows = {}
    for i, (p, m) in enumerate(zip(P, Sd)):
        if m:
            rows.setdefault(i // W, []).append(p)
    rows = {k: _median(v) for k, v in rows.items()}
    ringpx = [p for p, m in zip(P, Rd) if m and (p[3] > 40) and abs(p[3] - bgc[3]) + sum(abs(p[i] - bgc[i]) for i in range(3)) > 60]
    olc = _median(ringpx) if len(ringpx) > 0.25 * max(1, sum(1 for m in Rd if m)) else None
    if olc and rows and min(sum(abs(olc[i] - r[i]) for i in range(4)) for r in rows.values()) < 40:
        olc = None                                     # 테두리가 채움과 같으면 테두리 없음
    # 지우기: 글자+테두리 자리를 바탕색으로
    er = S.filter(ImageFilter.MaxFilter(7))
    img.paste(Image.new("RGBA", er.size, bgc), (X0, Y0), er)
    # 새 글자
    oo = dict(o)
    oo.setdefault("h", y1 - y0 + 1)
    oo.setdefault("track", 2)
    oo.setdefault("w", x1 - x0)
    oo["color"] = (255, 255, 255, 255)
    t = render_text(text, oo)
    K = t.split()[3]
    al = o.get("align", "l")
    x = x0 if al == "l" else (x0 + x1 - t.width) // 2 if al == "c" else x1 - t.width
    y = y0 + (y1 - y0 - t.height) // 2
    ks = sorted(rows) or [0]
    if olc:
        Ko = K.filter(ImageFilter.MaxFilter(3))
        img.paste(Image.new("RGBA", K.size, olc), (int(x), int(y)), Ko)
    col = Image.new("RGBA", K.size)
    for yy in range(K.height):
        ry = y + yy - Y0
        r = rows.get(ry) or rows[min(ks, key=lambda k: abs(k - ry))] if rows else (128, 128, 128, 255)
        col.paste(r, (0, yy, K.width, yy + 1))
    img.paste(col, (int(x), int(y)), K)
    return img


def restyle(img, box, text, o):
    x0, y0, x1, y1 = box
    reg = img.crop(box)
    W, H = reg.size
    m = o.get("m", 3)
    P = reg.load()
    rowbg = []
    for y in range(H):
        e = [P[x, y] for x in list(range(m)) + list(range(W - m, W))]
        rowbg.append(_median(e))
    thr = o.get("thr", 48)
    S = Image.new("L", (W, H), 0)
    Sp = S.load()
    for y in range(H):
        b = rowbg[y]
        for x in range(W):
            p = P[x, y]
            if max(abs(p[i] - b[i]) for i in range(4)) > thr:
                Sp[x, y] = 255
    if not S.getbbox():
        return img
    ow = o.get("ow", 3)
    core = S.filter(ImageFilter.MinFilter(2 * ow + 1))
    if not core.getbbox():
        core = S
    ring = ImageChops.subtract(S, core)
    rows, rp = {}, []
    Cp, Rp = core.load(), ring.load()
    for y in range(H):
        for x in range(W):
            if Cp[x, y]:
                rows.setdefault(y, []).append(P[x, y])
            elif Rp[x, y] and P[x, y][3] > 150:
                rp.append(P[x, y])
    allc = [p for v in rows.values() for p in v]
    if o.get("grad"):
        rows = {k: _median(v) for k, v in rows.items()}
    else:                                              # 기본: 채움 한 색 (번짐이 줄별 값에 섞이지 않게)
        f = _median(allc)
        rows = {k: f for k in rows}
    if "fill" in o:
        rows = {k: o["fill"] for k in rows} or {0: o["fill"]}
    olc = o.get("ol", _median(rp))
    glow = o.get("glow", 0)
    # 지우기: clear = 상자 전체 투명 (투명 바탕 위 글자), 아니면 글자 자리를 줄별 바탕색으로
    if o.get("clear"):
        img.paste((0, 0, 0, 0), o.get("clearbox", box))
    else:
        er = S.filter(ImageFilter.MaxFilter(2 * glow + 7 if glow else 7))
        Ep = er.load()
        for y in range(H):
            for x in range(W):
                if Ep[x, y]:
                    P[x, y] = rowbg[y]
        img.paste(reg, (x0, y0))
    # 쓰기
    bx0, by0, bx1, by1 = S.getbbox()
    oo = dict(o)
    oo.setdefault("h", int((by1 - by0 - 2 * ow) * 0.85))
    oo.setdefault("w", bx1 - bx0 - 2 * ow)
    oo["color"] = (255, 255, 255, 255)
    oo.pop("stroke", None)
    t = render_text(text, oo)
    K = t.split()[3]
    pad = ow + glow + 2
    Kp = Image.new("L", (K.width + 2 * pad, K.height + 2 * pad), 0)
    Kp.paste(K, (pad, pad))
    al = o.get("align", "c")
    cx = x0 + (bx0 + bx1) // 2
    x = cx - Kp.width // 2 if al == "c" else x0 + bx0 - pad + ow if al == "l" else x0 + bx1 + pad - ow - Kp.width
    y = y0 + (by0 + by1) // 2 - Kp.height // 2
    if glow:
        gc = o.get("glow_color") or olc or (255, 255, 255, 255)
        g = Kp.filter(ImageFilter.MaxFilter(2 * ow + 1)).filter(ImageFilter.GaussianBlur(glow))
        lay = Image.new("RGBA", Kp.size, gc[:3] + (0,))
        lay.putalpha(g.point(lambda v: min(255, v * 2)))
        img.alpha_composite(lay, (x, y))
    if olc and ow:
        lay = Image.new("RGBA", Kp.size, olc[:3] + (0,))
        lay.putalpha(Kp.filter(ImageFilter.MaxFilter(2 * ow + 1)))
        img.alpha_composite(lay, (x, y))
    col = Image.new("RGBA", Kp.size)
    ks = sorted(rows)
    for yy in range(Kp.height):
        ry = y + yy - y0
        r = rows.get(ry) or rows[min(ks, key=lambda k: abs(k - ry))]
        col.paste(r[:3] + (255,), (0, yy, Kp.width, yy + 1))
    col.putalpha(Kp)
    img.alpha_composite(col, (x, y))
    return img


def apply_ops(img, ops):
    for op in ops:
        k = op[0]
        if k == "canvas":
            img = Image.new("RGBA", op[1], (0, 0, 0, 0))
        elif k == "erase":
            img.paste((0, 0, 0, 0), op[1])
        elif k == "erasecol":
            x0, y0, x1, y1 = op[1]
            for y in range(y0, y1):
                for x in range(x0, x1):
                    p = img.getpixel((x, y))
                    if max(abs(p[i] - op[2][i]) for i in range(3)) <= op[3]:
                        img.putpixel((x, y), (0, 0, 0, 0))
        elif k == "fill":
            img.paste(op[2], op[1])
        elif k == "paste":
            _, src = load(os.path.join(DATA, op[1]))
            img.paste(src.crop(op[2]), op[2][:2])
        elif k == "scaled":
            src = DONE[op[1]]
            r = img.width / src.width
            c = src.crop(op[2])
            c = c.resize((max(1, round(c.width * r)), max(1, round(c.height * r))), Image.LANCZOS)
            img.alpha_composite(c, op[3])
        elif k == "retext":
            img = retext(img, op[1], op[2], op[3] if len(op) > 3 else {})
        elif k == "relabel":
            img = relabel(img, op[1], op[2], op[3], load(os.path.join(DATA, op[4]))[1])
        elif k == "restyle":
            img = restyle(img, op[1], op[2], op[3] if len(op) > 3 else {})
        elif k == "vfill":
            x0, y0, x1, y1 = op[1]
            row = img.crop((x0, op[2], x1, op[2] + 1))
            for y in range(y0, y1):
                img.paste(row, (x0, y))
        elif k == "copy":
            img.paste(img.crop(op[1]), op[2])
        elif k == "text":
            t = render_text(op[1], op[3])
            x, y = op[2]
            al = op[3].get("align", "l")
            x = x - t.width // 2 if al == "c" else x - t.width if al == "r" else x
            img.alpha_composite(t, (int(x), int(y)))
    return img


def main(apply, groups):
    global BGRA_HDR
    BGRA_HDR = _bgra_hdr()
    groups = groups or list(JOBS)
    os.makedirs(PREVIEW, exist_ok=True)
    for g in groups:
        for rel, ops in JOBS[g]:
            hdr, img = load(os.path.join(DATA, rel))
            out = apply_ops(img.copy(), ops)
            DONE[rel] = out
            bg = Image.new("RGBA", out.size, (90, 90, 140, 255))
            bg.alpha_composite(out)
            prev = os.path.join(PREVIEW, rel.replace("/", "__").replace(":", "_").replace("#", "_") + ".png")
            bg.convert("RGB").save(prev)
            if apply:
                save(os.path.join(MOD, rel), hdr, out)
            print(("썼음 " if apply else "미리보기 ") + rel)


if __name__ == "__main__":
    a = sys.argv[1:]
    main("--apply" in a, [x for x in a if not x.startswith("--")])
