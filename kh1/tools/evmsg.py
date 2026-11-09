"""EvMsg (.binl) 메시지 파서 / 직렬화.

구조 (exe 0x1A43A0 의 메시지 스캐너 0x1A45D0 기준, docs/file-formats.md):
  "EvMsg" + 언어 2바이트 + u32 메시지 수 + 메시지 N개 (순서대로 이어짐, 오프셋 표 없음) + 패딩
  메시지 번호 = 순서. 메시지 끝 = 0x04 또는 0x00 (끝 바이트 포함).

바이트 하나(위치 = 코드 경계)의 길이:
  0x04, 0x00            메시지 끝
  0x05 0x06 0x07        3바이트 (코드 + 2)
  0x0B, 0x0D            4바이트
  0x0A                  다음 바이트가 0 이면 4바이트, 아니면 2바이트
  0x09 0x0C 0x0E~0x1F   2바이트 (0x18~0x1F 는 2바이트 글자 포함)
  그 외 (0x01 0x02 0x03 0x08, 0x20 이상)  1바이트

사용 (openkh_venv python -I):
  python tools/evmsg.py check <파일...>     파싱 후 메시지 수/끝 위치/재직렬화 일치 확인
  python tools/evmsg.py dump <파일> [시작] [개수]
"""
import struct, sys

# 대화창 글꼴 1바이트 코드 (knj0 셀 그림으로 확인, 2026-10-29). 코드 = idx + 0x20.
# 아이콘(0x7A~0x9D), 장식 글자(0xAC~0xC9) 와 빈 칸은 표에 없다 -> {XX} 로 표기.
LATIN = {0x01: " ", 0x20: "―", 0xFA: "—"}
for i, ch in enumerate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"):
    LATIN[0x21 + i] = ch
for i, ch in enumerate("!?&%+-×/*.,・:;…–‒~'\"„()"):    # 0x76~0x79 '[]<>' 는 표기 구분자와 겹쳐 {76} 등으로 쓴다
    LATIN[0x5F + i] = ch
for i, ch in enumerate("¡¿ÀÁÂÄÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜßàáâäçèéêëìíîïñòóôöùúûü°"):
    LATIN[0xCA + i] = ch
LATIN[0xFB], LATIN[0xFC] = "»", "«"
CHAR_CODE = {v: k for k, v in LATIN.items()}

# 2바이트 첫 바이트 0x1A 는 msg_layout 이 공백으로 처리한다 (idx 480~735 사용 불가)
BAD_LEAD = 0x1A


def idx_to_bytes(idx):
    if idx < 224:
        return bytes([idx + 0x20])
    v = idx + 0x1820
    if not 0x1900 <= v <= 0x1FFF or v >> 8 == BAD_LEAD:
        raise ValueError(f"idx {idx} 는 메시지에 쓸 수 없음")
    return v.to_bytes(2, "big")


def code_len(b, i):
    c = b[i]
    if c in (0x05, 0x06, 0x07):
        return 3
    if c in (0x0B, 0x0D):
        return 4
    if c == 0x0A:
        return 4 if b[i + 1] == 0 else 2
    if 0x09 <= c <= 0x1F:
        return 2
    return 1


# 시스템(UI) 글꼴 문자열의 코드 길이 (42차, exe 0x28f820 문자열 넘기기 / 0x2D0E10 측정 / 0x2CFBF0 그리기).
# 대화창과 다르다: 0x0D x 이동·0x0E y 이동·0x11~0x14 는 3바이트, 0x08 은 5바이트, 0x05~0x07 정렬 등은 1바이트.
UI_END = (0x00, 0x10)


def code_len_ui(b, i):
    c = b[i]
    if 0x15 <= c < 0x20:
        return 2
    if c >= 0x20:
        return 1
    return {0x03: 2, 0x07: 2, 0x0C: 2, 0x0F: 2, 0x08: 5, 0x0B: 4,
            0x0D: 3, 0x0E: 3, 0x11: 3, 0x12: 3, 0x13: 3, 0x14: 3}.get(c, 1)


def split_ui(b, count):
    """UI 문자열 목록 (btltbl 의 Word/ItemHelp/AbilityName/AbilityHelp): 앞에서부터 count 개. 돌려줌: (목록, 끝 위치)."""
    msgs, i = [], 0
    for _ in range(count):
        j = i
        while b[j] not in UI_END:
            j += code_len_ui(b, j)
        msgs.append(b[i:j + 1])
        i = j + 1
    return msgs, i


def parse_v361(b):
    """"Message v361" 형식: remastered/menu/uk/sysmsg.bin/UK_sysmsg.binl (42차, exe 0x2d1570 이 고정 버퍼 0x2E1AC60
    (0x4800B) 에 복사, +0x10 표 위치, +0x14 데이터 위치를 UI 메시지 표 0x2e1ac48/50 으로 건다).
    머리말: 'Message v361' + u32 수 + u32 표 위치 + u32 데이터 위치 + u32 표 크기 + u32 데이터 길이.
    표 = u16 데이터 안 오프셋. 데이터는 시스템 글꼴 문자열 (split_ui 규칙).
    돌려줌: (조각 목록, {표 칸: 조각 번호})."""
    if b[:12] != b"Message v361":
        raise ValueError("Message v361 아님")
    _, to, do, tl, dl = struct.unpack_from("<5I", b, 12)
    offs = struct.unpack_from(f"<{tl // 2}H", b, to)
    data = b[do:do + dl]
    segs, starts, i = [], [], 0
    while i < dl:
        j = i
        while data[j] not in UI_END:
            j += code_len_ui(data, j)
        starts.append(i)
        segs.append(data[i:j + 1])
        i = j + 1
    return segs, {slot: starts.index(v) for slot, v in enumerate(offs)}


def serialize_v361(segs, refs, b):
    """parse_v361 의 역. 머리말·표 위치는 그대로, 데이터 길이와 오프셋만 새로 쓴다. 16 배수로 CD 채움."""
    _, to, do, tl, _ = struct.unpack_from("<5I", b, 12)
    starts, p = [], 0
    for s in segs:
        starts.append(p)
        p += len(s)
    if p > 0xFFFF:
        raise ValueError("u16 오프셋 범위 초과")
    out = bytearray(b[:do])
    struct.pack_into("<I", out, 28, p)
    for slot, k in refs.items():
        struct.pack_into("<H", out, to + slot * 2, starts[k])
    out += b"".join(segs)
    out += b"\xcd" * (-len(out) % 16)
    return bytes(out)


def split_messages(b, start, count):
    """start 부터 count 개 메시지를 잘라 (bytes 목록, 끝 위치) 를 돌려준다."""
    msgs, i = [], start
    for _ in range(count):
        j = i
        while b[j] not in (0x00, 0x04):
            j += code_len(b, j)
        msgs.append(b[i:j + 1])
        i = j + 1
    return msgs, i


def parse(b):
    if b[:5] != b"EvMsg":
        return parse_plain(b)
    count = int.from_bytes(b[7:11], "little")
    msgs, end = split_messages(b, 11, count)
    return b[:11], msgs, b[end:]


def parse_plain(b):
    """머리말 없는 형식: u32 메시지 수 + 메시지 N개 + 패딩(00/CD). exchange/*_item_shop_msg.bin 등 (37차).
    head 는 b"" 이라 serialize 가 그대로 u32 수 + 메시지 + 꼬리를 만든다."""
    count = int.from_bytes(b[:4], "little")
    if not 0 < count < 2000:
        raise ValueError("메시지 수 이상")
    msgs, end = split_messages(b, 4, count)
    if any(x not in (0x00, 0xCD) for x in b[end:]):
        raise ValueError("꼬리가 패딩이 아님")
    return b"", msgs, b[end:]


def serialize(head, msgs, tail):
    return head[:7] + len(msgs).to_bytes(4, "little") + b"".join(msgs) + tail


def parse_ofs(data, ofs, ui=False):
    """데이터 + u16 오프셋 표 형식: exchange/UK_SAWEMSG.BIN + UK_SAWEOMSG.BIN, wname_data + wname_offset 등 (38차).
    데이터를 처음부터 끝 코드 단위로 잘라 조각 목록을 만든다 (SAWEMSG 는 메시지 뒤에 '00 91 00' 같은
    부가 바이트가 있어 표가 가리키지 않는 조각도 생긴다). 표 값 중 데이터 안을 가리키는 것만 오프셋이고,
    0 은 빈 칸이거나 첫 메시지, CD 등 범위 밖 값은 그대로 둔다.
    돌려줌: (조각 목록, 꼬리, {표 칸: 조각 번호}). 조각 중간을 가리키는 값이 있으면 ValueError."""
    vals = [int.from_bytes(ofs[i:i + 2], "little") for i in range(0, len(ofs) - 1, 2)]
    last = max(v for v in vals if v < len(data))
    segs, starts, i = [], [], 0
    while i <= last:          # ui: 시스템 글꼴 코드 길이 (SASAMSG, 42차)
        j = i
        while data[j] not in ((0x00, 0x10) if ui else (0x00, 0x04)):
            j += code_len_ui(data, j) if ui else code_len(data, j)
        starts.append(i)
        segs.append(data[i:j + 1])
        i = j + 1
    if any(x not in (0x00, 0xCD) for x in data[i:]):
        raise ValueError("꼬리가 패딩이 아님")
    refs = {}
    for slot, v in enumerate(vals):
        if v < i:
            if v not in starts:
                raise ValueError(f"표 칸 {slot} 이 조각 중간({v})을 가리킴")
            refs[slot] = starts.index(v)
    return segs, data[i:], refs


def serialize_ofs(segs, tail, refs, data, ofs):
    """parse_ofs 의 역. 원래 크기보다 짧으면 CD 로 채워 크기를 지키고, 길면 16 배수로 늘린다
    (로더가 고정 버퍼인지 미확인 -> 길어지면 build 가 경고). 돌려줌: (새 데이터, 새 표)."""
    body = b"".join(segs) + tail
    size = len(data) if len(body) <= len(data) else -(-len(body) // 16) * 16
    starts, p = [], 0
    for s in segs:
        starts.append(p)
        p += len(s)
    if p > 0xFFFF:
        raise ValueError("u16 오프셋 범위 초과")
    nofs = bytearray(ofs)
    for slot, k in refs.items():
        nofs[slot * 2:slot * 2 + 2] = starts[k].to_bytes(2, "little")
    return body + b"\xcd" * (size - len(body)), bytes(nofs)


def tokens(m, ui=False):
    """메시지를 (종류, bytes) 로 나눈다. 종류: 'ch' 1바이트 글자, 'ch2' 2바이트 글자, 'ctl' 제어, 'end'.
    ui: 시스템 글꼴 문자열 규칙 (code_len_ui, 끝 00/10, 2바이트 글자 0x15~0x1F)."""
    out, i = [], 0
    while i < len(m):
        c = m[i]
        if c in (UI_END if ui else (0x00, 0x04)):
            out.append(("end", m[i:i + 1])); i += 1; continue
        n = code_len_ui(m, i) if ui else code_len(m, i)
        if c >= 0x20 or c == 0x01:
            kind = "ch"
        elif (0x15 if ui else 0x18) <= c <= 0x1F:
            kind = "ch2"
        else:
            kind = "ctl"
        out.append((kind, m[i:i + n]))
        i += n
    return out


def show(m, glyphs=None, ui=False):
    """메시지 바이트 -> 사람이 읽는 표기. 줄바꿈 0x02 = '\\n', 제어 = [hex], 표에 없는 글자 = {hex}, 끝 = <hex>.
    glyphs: {bytes: 글자} (한글 등 배정된 글자). ui: tokens 참고."""
    s = []
    for k, t in tokens(m, ui):
        if glyphs and t in glyphs:
            s.append(glyphs[t])
        elif k == "ch":
            s.append(LATIN.get(t[0], f"{{{t[0]:02X}}}"))
        elif k == "ch2":
            s.append(f"{{{t.hex().upper()}}}")
        elif k == "end":
            s.append(f"<{t[0]:02X}>")
        elif t == b"\x02":
            s.append("\\n")
        else:
            s.append(f"[{t.hex(' ').upper()}]")
    return "".join(s)


def encode(text, glyphs=None):
    """show() 의 역. glyphs: {글자: bytes}. 없는 글자는 KeyError."""
    out, i = bytearray(), 0
    while i < len(text):
        c = text[i]
        if c in "[{<":
            j = text.index({"[": "]", "{": "}", "<": ">"}[c], i)
            out += bytes.fromhex(text[i + 1:j])
            i = j + 1
        elif text.startswith("\\n", i):
            out.append(0x02); i += 2
        elif glyphs and c in glyphs:
            out += glyphs[c]; i += 1
        elif c in CHAR_CODE:
            out.append(CHAR_CODE[c]); i += 1
        else:
            raise KeyError(f"글자 {c!r} (U+{ord(c):04X}) 의 코드가 없음: {text!r}")
    return bytes(out)


def main(a):
    if not a:
        print(__doc__); return 2
    if a[0] == "check":
        bad = 0
        for f in a[1:]:
            b = open(f, "rb").read()
            if b[:5] != b"EvMsg":
                continue
            try:
                head, msgs, tail = parse(b)
                ok = serialize(head, msgs, tail) == b and set(tail) <= {0xCD, 0x00}
            except (IndexError, ValueError) as e:
                ok, msgs, tail = False, [], b""
                print(f"FAIL {f}: {e}")
            if not ok:
                bad += 1
                print(f"BAD  {f}: msgs={len(msgs)} tail={tail[:16].hex(' ')} ({len(tail)}B)")
        print(f"files={len(a) - 1} bad={bad}")
    elif a[0] == "dump":
        head, msgs, tail = parse(open(a[1], "rb").read())
        s = int(a[2]) if len(a) > 2 else 0
        n = int(a[3]) if len(a) > 3 else len(msgs)
        for k in range(s, min(s + n, len(msgs))):
            print(f"{k:5d} {show(msgs[k])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
