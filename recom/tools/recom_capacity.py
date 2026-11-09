"""한글에 쓸 수 있는 글리프 칸 수 (sysfont / evtfont).

칸 g 를 쓸 수 있는 조건:
  - 폭 표 안 (g < 폭 개수)
  - UK 텍스트가 쓰는 코드, 게임이 직접 그리는 코드(GAME_CODES)의 글리프가 아님 (+ 0번 □)
  - 칸 안 원본 그림이 비었거나, 매핑 표가 가리키는 글리프(가나 등, 영어판에서 안 씀)
  - 보호 영역 밖: sysfont 3쪽 6행 이후 (HD 버튼 아이콘 그림)
사용: python recom_capacity.py <Recom 추출 폴더>
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import recom_ctd, recom_ffmw, recom_fontgrid as fg, recom_paths as P, recom_textfile as TF


# 텍스트 파일 밖에서 게임(exe)이 그리는 코드 (게임 확인 2026-11-09: 덱 편집 "×03" 이 "하03", 이름 입력 키보드가 한글로 나옴)
#  - ASCII 전체: 1바이트 코드라 다른 칸으로 옮길 수 없다 (키보드의 * = @ _ 등은 UK 텍스트에 없음)
#  - UK 이름 입력 키보드 표: exe .rdata 0x50C1FC, u32 x 131 (A a B b ... 악센트 문자는 UK 글꼴이 0x9980~0x99BA 칸에 넣음)
#  - exe 화면 문자열의 기호: "×%02d" 0x5091A0, "×{F9}D%d" 0x51799C, "%4d {F9}Y→{F9}R%4d" 0x512C70,
#    "%s／%3d：%02d　%s%s" 0x51B150, "☆　★◎" 0x51B168, "　♪" 0x51B174, "＊..." 0x510CA0
KEYBOARD_UK = [0x41, 0x61, 0x42, 0x62, 0x43, 0x63, 0x44, 0x64, 0x45, 0x65, 0x9980, 0x999A, 0x9981, 0x999B, 0x9982, 0x999C,
               0x9983, 0x999D, 0x9986, 0x99A0, 0x30, 0x31, 0x32, 0x33, 0x34, 0x46, 0x66, 0x47, 0x67, 0x48, 0x68, 0x49, 0x69,
               0x4A, 0x6A, 0x9987, 0x99A1, 0x9988, 0x99A2, 0x9989, 0x99A3, 0x998A, 0x99A4, 0x998B, 0x99A5, 0x35, 0x36, 0x37,
               0x38, 0x39, 0x4B, 0x6B, 0x4C, 0x6C, 0x4D, 0x6D, 0x4E, 0x6E, 0x4F, 0x6F, 0x998C, 0x99A6, 0x998D, 0x99A7, 0x998F,
               0x99A9, 0x9990, 0x99AA, 0x9991, 0x99AB, 0x20, 0x21, 0x3F, 0x23, 0x26, 0x50, 0x70, 0x51, 0x71, 0x52, 0x72, 0x53,
               0x73, 0x54, 0x74, 0x9993, 0x99AD, 0x9995, 0x99AE, 0x9996, 0x99AF, 0x9997, 0x99B0, 0x9998, 0x99B1, 0x2A, 0x2B,
               0x2D, 0x2F, 0x3D, 0x55, 0x75, 0x56, 0x76, 0x57, 0x77, 0x58, 0x78, 0x59, 0x79, 0x9985, 0x999F, 0x998E, 0x99A8,
               0x9999, 0x9994, 0x99B2, 0x22, 0x27, 0x2C, 0x2E, 0x3A, 0x5A, 0x7A, 0x99B6, 0x99B9, 0x99BA, 0x99B4, 0x99B3,
               0x40, 0x5F]
EXE_SYMBOLS = [0x817E, 0x81A8, 0x815E, 0x8146, 0x8140, 0x8199, 0x819A, 0x819D, 0x81F4, 0x8196]
GAME_CODES = set(range(0x20, 0x7F)) | set(KEYBOARD_UK) | set(EXE_SYMBOLS)


def used_codes(data):
    """지켜야 할 코드 = UK 텍스트(.ctdl, MVS)가 쓰는 코드 + GAME_CODES."""
    s = set(GAME_CODES)
    for rel in P.uk_text(data):                     # .ctdl + 영상 자막 MVS
        for m in TF.parse(rel, open(os.path.join(data, rel), "rb").read())["msgs"]:
            s.update(c for c in fg.codes(m) if c >= 0x20)
    return s


def protected(kind, g):
    L = fg.LAYOUT[kind]
    per = L["cols"] * L["rows"]
    return kind == "sys" and g // per == 3 and (g % per) // L["cols"] >= 6


def free_cells(data, kind, used=None):
    R = os.path.join(data, "remastered", "SYS", "0001")
    b = open(os.path.join(R, "SY0001.BIN", f"UK_{kind}font.binl"), "rb").read()
    ff = recom_ffmw.parse(b)
    nw = ff["a"] - 0x10
    used = used if used is not None else used_codes(data)
    keep = {0}
    for c in used:
        try:
            keep.add(ff["map"][fg.code_index(c)])
        except (ValueError, IndexError):
            pass
    A = Image.open(os.path.join(R, "SY0001.VTM", f"UK_{kind}font_fo240.png")).getchannel("A")
    n = fg.LAYOUT[kind]["cell"]
    out = []
    for g in range(nw):
        if g in keep or protected(kind, g):
            continue
        x, y = fg.cell_xy(kind, g)
        if x + n > A.width or y + n > A.height:
            continue
        out.append(g)
    return out, keep


if __name__ == "__main__":
    data = sys.argv[1]
    used = used_codes(data)
    print("지킬 글자 코드 (UK 텍스트 + 게임이 직접 그리는 코드)", len(used), "종")
    for kind in ("sys", "evt"):
        free, keep = free_cells(data, kind, used)
        print(f"{kind}: 쓸 수 있는 칸 {len(free)} (지킬 글리프 {len(keep)})")
