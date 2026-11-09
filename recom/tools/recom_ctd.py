"""Re:COM `@CTD` 텍스트 파일 읽기/쓰기 (recom/docs/file-formats.md).

구조 (UK .ctdl 로 확인):
  0x00 "@CTD", 0x04 u16 레이아웃 수, 0x06 u16 메시지 수, 0x08 u32 오프셋 표 위치, 0x0C u32 문자열 영역 시작
  표 = u32 x 메시지 수, 값은 문자열 영역 기준 상대 오프셋. 문자열은 NUL 끝.
원본 CTD(.CTD)는 앞에 0x40 바이트 이름 헤더가 붙은 컨테이너일 수 있다 -> find_ctd 로 "@CTD" 위치를 찾는다.

사용:
  python recom_ctd.py dump <파일> [시작오프셋]          메시지 목록
  python recom_ctd.py find <폴더> <문자열>              UK_*.ctdl / *.CTD 에서 문자열 검색
"""
import os, struct, sys


def find_ctd(b):
    i = b.find(b"@CTD")
    if i < 0:
        raise ValueError("@CTD 없음")
    return i


def parse(b, base=None):
    """-> dict(base, n_lay, tbl, txt, msgs=[bytes], ends)."""
    if base is None:
        base = find_ctd(b)
    n_lay, n_msg, tbl, txt = struct.unpack_from("<HHII", b, base + 4)
    msgs = []
    for i in range(n_msg):
        o = base + txt + struct.unpack_from("<I", b, base + tbl + 4 * i)[0]
        e = b.index(b"\0", o)
        msgs.append(b[o:e])
    return dict(base=base, n_lay=n_lay, tbl=tbl, txt=txt, msgs=msgs)


def build(b, d, msgs):
    """같은 헤더·레이아웃으로 문자열 영역을 다시 쓴다. 문자열 영역 뒤 원본 내용은 버리고 4바이트 정렬.
    원본 CTD 컨테이너(base>0)는 헤더 크기 필드를 모르므로 지원하지 않는다."""
    if d["base"] != 0:
        raise ValueError("컨테이너 CTD 는 아직 지원하지 않음 (.ctdl 만)")
    out = bytearray(b[:d["txt"]])
    for i, m in enumerate(msgs):
        struct.pack_into("<I", out, d["tbl"] + 4 * i, len(out) - d["txt"])
        out += m + b"\0"
        while len(out) % 4:
            out += b"\0"
    out += b"\0" * 4                    # 원본 규칙 (426 파일 확인): 마지막 문자열 뒤 0 4바이트, 0xCD 로 16 배수
    while len(out) % 16:
        out += b"\xcd"
    return bytes(out)


def show(m):
    return "".join(chr(x) if 0x20 <= x < 0x7F else ("\\n" if x == 0x0A else f"{{{x:02X}}}") for x in m)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "dump":
        b = open(sys.argv[2], "rb").read()
        d = parse(b, int(sys.argv[3], 0) if len(sys.argv) > 3 else None)
        print(f"base {d['base']:#x} 레이아웃 {d['n_lay']} 메시지 {len(d['msgs'])}")
        for i, m in enumerate(d["msgs"]):
            print(f"{i:4d}  {show(m)}")
    elif c == "find":
        key = sys.argv[3].encode()
        for dp, dns, fns in os.walk(sys.argv[2]):
            for f in fns:
                if f.startswith("UK_") and f.endswith(".ctdl"):
                    p = os.path.join(dp, f)
                    b = open(p, "rb").read()
                    try:
                        d = parse(b)
                    except Exception:
                        continue
                    for i, m in enumerate(d["msgs"]):
                        if key in m:
                            print(f"{os.path.relpath(p, sys.argv[2])}  #{i}  {show(m)[:90]}")
