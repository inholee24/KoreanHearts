"""Re:COM 영상 자막 `MVS` (remastered/FORM/5000/FO5000.BIN/<언어>_MVS000.binl) 읽기·쓰기.

형식 (5개 언어 파일로 확인, 2026-11-05):
  +0x00 "MVS\\0"   +0x04 u16 0   +0x06 u16 항목 수 n   +0x08 u32 문자열 영역 시작 (0x30)   +0x0C 0
  +0x10 항목 n 개 x 8 B: u16 시작, u16 끝 (영상 시각, 단위 미확인 - 바꾸지 않음), u32 문자열 위치 (파일 기준)
  문자열: CTD 와 같은 인코딩 (0x80 이상 2바이트, 0x0A 줄바꿈), 0 으로 끝, 다음 문자열은 4바이트 정렬(0), 파일 끝은 0xCD 로 16 배수.
사용: python -I recom_mvs.py <binl>... (왕복 확인: 다시 만든 바이트가 원본과 같은지)
"""
import struct, sys


def parse(b):
    assert b[:4] == b"MVS\0", "MVS 아님"
    n = struct.unpack_from("<H", b, 6)[0]
    start = struct.unpack_from("<I", b, 8)[0]
    ents = [struct.unpack_from("<HHI", b, 0x10 + 8 * i) for i in range(n)]
    msgs = [b[o:b.index(b"\0", o)] for _, _, o in ents]
    return dict(n=n, start=start, ents=ents, msgs=msgs)


def build(b, d, msgs):
    """같은 머리말·시각으로 문자열만 다시 쓴다."""
    out = bytearray(b[:d["start"]])
    for i, ((t0, t1, _), m) in enumerate(zip(d["ents"], msgs)):
        struct.pack_into("<HHI", out, 0x10 + 8 * i, t0, t1, len(out))
        out += m + b"\0"
        while len(out) % 4:
            out += b"\0"
    while len(out) % 16:                 # 5개 언어 확인: 4바이트 정렬(0) 뒤 0xCD 로 16 배수 (CTD 와 달리 0 4바이트 없음)
        out += b"\xcd"
    return bytes(out)


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        b = open(p, "rb").read()
        d = parse(b)
        ok = build(b, d, d["msgs"]) == b
        bad += not ok
        print(("같음 " if ok else "다름 ") + p, d["n"], [m[:30] for m in d["msgs"]])
    sys.exit(1 if bad else 0)
