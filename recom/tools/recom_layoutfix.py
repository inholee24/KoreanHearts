"""레이아웃(창) 크기 보정: 번역이 원문보다 넓거나 줄이 많으면 창 폭·높이를 그만큼 늘린다 (빌드·검증 공용).

근거 (file-formats.md "레이아웃 사각형", 2026-11-05 exe 분석):
  - 0x2B1563 이 레이아웃 +0x16/+0x18 (위치), +0x1A/+0x1C (크기, 홀수면 +1), +0x1E 하위 바이트 (정렬),
    +0x22 (글자 크기) 를 읽어 0x2B1F70 (창 생성) 에 넘긴다. 창 틀(0x90 객체) 크기 = 이 값.
  - 정렬 1 = x 0x20, 2 = x 0x100 - w/2, 3 = x 0x1E0 - w (512 폭 좌표), 0 = 데이터 x.
  - 글은 0x25A380 이 따로 잰다. 잰 크기로 틀을 키우는 경로는 찾지 못했다 (추론: 없음).
  - 원문 단일 메시지 레이아웃: w - 글 폭(evt 폭 표 기준) p10 약 0, p50 +18~24 / h = 1줄 30, 2줄 52, 3줄 76
    -> 창 크기는 원문 글 크기 + 여백으로 미리 정해져 있다.
규칙: 레이아웃마다 Δ폭 = max(번역 최대 줄 폭 - 원문 최대 줄 폭) (sys/evt 두 폭 표 중 큰 쪽, 글자 크기 배율),
  Δ줄 = 번역 최대 줄 수 - 원문 최대 줄 수. w += ceil(Δ폭) (짝수로), h += Δ줄 x (크기 + 1).
  w 또는 h 가 0 인 레이아웃은 건드리지 않는다. 정렬 0 이면 오른쪽 끝이 max(원래 끝, 496) 을 넘을 때 x 를 왼쪽으로
  (최소 16), 아래 끝이 max(원래 끝, 440) 을 넘을 때 y 를 위로 (최소 16) 옮긴다. 줄이기는 하지 않는다.
"""
import math, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ffmw, recom_fontgrid as fg

CELL = {"sys": 20, "evt": 26}
RIGHT, BOTTOM, MARGIN = 496, 440, 16


def line_widths(m, ff, kind):
    """메시지 줄별 폭 (폭 표 단위, 글자 크기 = 칸 크기일 때 PS2 px). 공백 = 칸 x 3/8, 아이콘 = 칸, 색 = 0."""
    W, wofs, cell, out, w, i = ff["widths"], ff["wofs"], CELL[kind], [], 0, 0
    while i < len(m):
        c = m[i]
        if c == 0x0A:
            out.append(w); w = 0; i += 1; continue
        if c >= 0x80:
            t = m[i + 1] if i + 1 < len(m) else 0
            i += 2
            if c in (0xF5, 0xF6):
                w += cell; continue
            if c == 0xF9:
                continue
            code = (c << 8) | t
        else:
            i += 1
            if c < 0x20:
                continue
            if c == 0x20:
                w += cell * 3 / 8; continue
            code = c
        try:
            j = 0x10 + ff["map"][fg.code_index(code)] - wofs
            w += W[j] if 0 <= j < len(W) else cell
        except (ValueError, IndexError):
            w += cell
    out.append(w)
    return out


def ffs(font_objs):
    """recom_font.Font {kind: Font} -> {kind: FFMW dict} (메모리의 현재 표)."""
    return {k: recom_ffmw.parse(bytes(f.raw)) for k, f in font_objs.items()}


def fix(raw, msgs_o, msgs_t, ff_o, ff_t):
    """원본 CTD 바이트 + 원문/번역 메시지 -> (레이아웃을 고친 머리말 bytes [0:n_lay 끝], 바뀐 목록)."""
    n_lay = struct.unpack_from("<H", raw, 4)[0]
    head = bytearray(raw[:0x10 + 0x30 * n_lay])
    changes = []
    for k in range(n_lay):
        o = 0x10 + 0x30 * k
        start, cnt = struct.unpack_from("<H", head, o + 0x10)[0], struct.unpack_from("<H", head, o + 0x14)[0]
        x, y, w, h = struct.unpack_from("<4H", head, o + 0x16)
        mode = head[o + 0x1E]
        size = struct.unpack_from("<H", head, o + 0x22)[0]
        mo, mt = msgs_o[start:start + cnt], msgs_t[start:start + cnt]
        if not mo or mo == mt or not size or not w or not h:
            continue
        dw, dl = 0.0, 0
        for kind in CELL:
            lo = [line_widths(m, ff_o[kind], kind) for m in mo]
            lt = [line_widths(m, ff_t[kind], kind) for m in mt]
            wo = max(max(v) for v in lo) * size / CELL[kind]
            wt = max(max(v) for v in lt) * size / CELL[kind]
            dw = max(dw, wt - wo)
            dl = max(dl, max(len(v) for v in lt) - max(len(v) for v in lo))
        nw, nh = w, h                        # 늘어날 때만 고친다 (홀수 원본 값은 게임이 +1 하므로 그대로 둠)
        if dw > 0.5:
            nw = w + math.ceil(dw)
            nw += nw & 1
        if dl > 0:
            nh = h + dl * (size + 1)
            nh += nh & 1
        if nw == w and nh == h:
            continue
        nx, ny = x, y
        if mode == 0:
            r = max(x + w, RIGHT)
            if x + nw > r:
                nx = max(MARGIN, r - nw)
            b = max(y + h, BOTTOM)
            if y + nh > b:
                ny = max(MARGIN, b - nh)
        struct.pack_into("<4H", head, o + 0x16, nx, ny, nw, nh)
        changes.append((k, (x, y, w, h), (nx, ny, nw, nh)))
    return bytes(head), changes
