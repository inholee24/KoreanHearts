"""메뉴 위·세이브 파일의 장소 이름: exchange/UK_allarea.nam (42차).

형식: u32 월드 수 + 12B 0 + (u32 오프셋, u32 크기) x 월드. 월드 블록: u32 이름 수 + 12B 0 + (오프셋, 크기) x 이름
(블록 기준) + 이름들. 이름 = Shift-JIS 전각 문자열, 00 으로 끝나고 4B 단위로 0 채움.
exe: 로더 0x18e400 -> 고정 버퍼 0x234C0F0 (다음 전역 0x234E420 까지 0x2330 = 9,008B). 이름 얻기 0x18e4b0/0x18e500.
그리기(0x2d12e0 측정, 0x2d19a0 글자 찾기 등): 2바이트씩 읽어 시스템 글꼴 표 레코드 +0..1 (u16) 과 같은 레코드를
앞에서부터 [0x2E16BE8] 개 안에서 찾는다 (81 40 = 전각 공백은 따로). 그 수는 실행 중 0x230 = 560.
-> 한글은 sysfont.sjis_code(idx) 의 가짜 2바이트 코드를 레코드 +0..1 에 두고 여기 쓴다. idx 560 이상 레코드도
   찾게 하려면 mem.py tex2x 가 [0x2E16BE8] 을 1024 로 바꿔야 한다.
번역: translation/allarea.tsv (en<TAB>ko). en 은 반각으로 바꾼 원문.
"""
import os, struct

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REL = "exchange/UK_allarea.nam"
TSV = os.path.join(ROOT, "translation", "allarea.tsv")
LIMIT = 0x2330


def to_half(s):
    return "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else (" " if c == "　" else c) for c in s)


def parse(b):
    """[(월드, [이름 bytes ...]) ...]. 크기 0 인 월드는 빈 목록."""
    n = struct.unpack_from("<I", b, 0)[0]
    out = []
    for w in range(n):
        o, s = struct.unpack_from("<II", b, 0x10 + 8 * w)
        names = []
        if s:
            k = struct.unpack_from("<I", b, o)[0]
            for j in range(k):
                eo, es = struct.unpack_from("<II", b, o + 0x10 + 8 * j)
                names.append(b[o + eo:o + eo + es].split(b"\0")[0])
        out.append(names)
    return out


def en_of(name):
    return to_half(name.decode("cp932"))


def encode(text, codes):
    """한글은 codes[글자], 공백은 81 40, 나머지는 전각 Shift-JIS."""
    out = bytearray()
    for c in text:
        if c in codes:
            out += codes[c]
        elif c == " ":
            out += b"\x81\x40"
        elif 0x21 <= ord(c) <= 0x7E:
            out += chr(ord(c) + 0xFEE0).encode("cp932")
        else:
            out += c.encode("cp932")
    return bytes(out)


def serialize(worlds, head_size=0x130):
    """head_size: 첫 블록 위치 (원본 0x130 = 표 36칸 자리). 블록은 16B 단위로 0 채움."""
    n = len(worlds)
    head = bytearray(struct.pack("<I", n) + bytes(12))
    blocks = []
    for names in worlds:
        if not names:
            blocks.append(b"")
            continue
        k = len(names)
        hdr = bytearray(struct.pack("<I", k) + bytes(12) + bytes(8 * k))
        body, p = bytearray(), len(hdr)
        for j, nm in enumerate(names):
            s = nm + b"\0"
            s += bytes(-len(s) % 4)
            struct.pack_into("<II", hdr, 0x10 + 8 * j, p + len(body), len(s))
            body += s
        blk = bytes(hdr + body)
        blocks.append(blk + bytes(-len(blk) % 16))
    out = head + bytes(head_size - len(head))
    for w, blk in enumerate(blocks):
        struct.pack_into("<II", out, 0x10 + 8 * w, len(out), len(blk))
        out += blk
    out += bytes(-len(out) % 16)
    return bytes(out)


def read_tsv():
    m = {}
    if os.path.exists(TSV):
        with open(TSV, encoding="utf-8") as fp:
            next(fp)
            for line in fp:
                en, ko = line.rstrip("\n").split("\t")
                if ko:
                    m[en] = ko
    return m


def chars(tr):
    return {c for ko in tr.values() for c in ko if "가" <= c <= "힣"}


def build(b, tr, codes):
    """번역한 allarea.nam bytes. 번역이 없는 이름은 원문 그대로."""
    worlds = [[encode(tr[en_of(nm)], codes) if en_of(nm) in tr else nm for nm in names] for names in parse(b)]
    out = serialize(worlds)
    if len(out) > LIMIT:
        raise ValueError(f"{REL} {len(out)}B > 게임 버퍼 {LIMIT}B")
    return out


if __name__ == "__main__":
    b = open(os.path.join(ROOT, "data", "kh1", REL), "rb").read()
    print("왕복 일치:", serialize(parse(b)) == b, len(b))
