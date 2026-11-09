"""설정 메뉴 (Image/SettingMenu.pkg) 의 CTD 문자열 파일 읽기/쓰기 (45차 조사).

구조 (uk/ctd/ctmn000.ctd 바이트로 확인):
  0x00 "@CTD", 0x04 u32, 0x08 u32, 0x0C u16 레이아웃 수, 0x0E u16 메시지 수,
  0x10 u32 메시지 표 오프셋, 0x14 u32 레이아웃 표 오프셋 (20B 씩), 0x18 u32 문자열 영역 오프셋
  메시지 8B: u16 id, u16 flags, u16 문자열 오프셋 (파일 처음부터), u16 레이아웃 번호
  문자열: UTF-16LE, 0x0000 끝. 0x000A 줄바꿈, U+E000 대 사설 영역 = 버튼 아이콘 (추론)
"""
import struct, sys


def parse(b):
    assert b[:4] == b"@CTD"
    n_lay, n_msg = struct.unpack_from("<HH", b, 0x0C)
    mofs, lofs, tofs = struct.unpack_from("<III", b, 0x10)
    msgs = []
    for k in range(n_msg):
        mid, fl, so, lay = struct.unpack_from("<HHHH", b, mofs + 8 * k)
        e = so
        while b[e:e + 2] != b"\0\0":
            e += 2
        msgs.append(dict(id=mid, flags=fl, ofs=so, layout=lay, text=b[so:e].decode("utf-16le")))
    return dict(head=b[:tofs], n_lay=n_lay, mofs=mofs, tofs=tofs, msgs=msgs, tail_len=len(b))


def build(d, texts):
    """texts: 메시지 순서대로의 문자열. 문자열 영역을 다시 쓰고 오프셋을 고친다. 끝은 0xCD 로 16 배수 (원본과 같음)."""
    out = bytearray(d["head"])
    for k, t in enumerate(texts):
        so = len(out)
        if so > 0xFFFF:
            raise ValueError("문자열 오프셋이 u16 을 넘음")
        struct.pack_into("<H", out, d["mofs"] + 8 * k + 4, so)
        out += t.encode("utf-16le") + b"\0\0"
    out += b"\xCD" * (-len(out) % 16)
    return bytes(out)


def show(t):
    return "".join(f"{{{ord(c):04X}}}" if 0xE000 <= ord(c) <= 0xF8FF else c for c in t).replace("\n", "\\n")


if __name__ == "__main__":
    b = open(sys.argv[1], "rb").read()
    d = parse(b)
    print(f"레이아웃 {d['n_lay']}, 메시지 {len(d['msgs'])}, 문자열 영역 {d['tofs']:#x}, 파일 {len(b)}B")
    for m in d["msgs"]:
        print(f"{m['id']:04x} {m['flags']:04x} {m['ofs']:#06x} L{m['layout']:<3} {show(m['text'])}")
