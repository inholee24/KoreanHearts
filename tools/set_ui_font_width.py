"""mod\\kh1\\exchange\\US_font_data_tbl.bin 의 글자 레코드 +6(폭) 바이트를 바꾼다.

배경 (work-history 6-36): 선택지 창 폭 측정 함수(exe 0x2D0E10)는 대화창 폭 테이블
(UK_kanji.knj)이 아니라 이 UI 폰트 표(560 x 16B)의 +6 값을 더한다. 한글 칸의
+6 은 원래 자리 글자의 값이라 창 폭이 틀린다.

사용:
    python -I tools/set_ui_font_width.py <폭> <idx|idx-idx> [...] [--apply]
--apply 없이 실행하면 바뀔 값만 보여준다.
"""
import sys
from pathlib import Path

TBL = Path(__file__).resolve().parent.parent / "mod" / "kh1" / "exchange" / "US_font_data_tbl.bin"
REC, FIELD = 16, 6


def parse(specs):
    out = []
    for s in specs:
        a, _, b = s.partition("-")
        out.extend(range(int(a), int(b or a) + 1))
    return out


def main(argv):
    apply = "--apply" in argv
    args = [a for a in argv if a != "--apply"]
    if len(args) < 2:
        print(__doc__)
        return 2
    width, idxs = int(args[0]), parse(args[1:])
    data = bytearray(TBL.read_bytes())
    for i in idxs:
        off = i * REC + FIELD
        print(f"idx {i:4d} @ {off:#06x}: {data[off]} -> {width}")
        data[off] = width
    if apply:
        TBL.write_bytes(data)
    print(f"apply: {apply}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
