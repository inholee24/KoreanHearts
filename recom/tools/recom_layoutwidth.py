"""레이아웃 필드와 원문 줄 폭 비교 (창 폭 필드·자동 줄바꿈 여부를 데이터로 판정).

레이아웃 k (0x30 B, CTD+0x10+k*0x30): +0x10 u16 시작 메시지, +0x14 u16 메시지 수 (FO0111 에서 합 = 메시지 수 확인).
줄 폭 = 글자 폭 표(UK sysfont/evtfont binl [0x10+glyph]) 합 (단위: 폭 표 단위, 1 = HD 2px = PS2 1px 로 추정).
필드 후보 +0x16 +0x18 +0x1A +0x1C 와 (최대 줄 폭 x 글자크기/칸크기) 의 비율 분포를 본다.
사용: python -I recom_layoutwidth.py <Recom 추출 폴더> [sys|evt]
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ctd, recom_ffmw, recom_fontgrid as fg

data = sys.argv[1]
kind = sys.argv[2] if len(sys.argv) > 2 else "sys"
R = os.path.join(data, "remastered", "SYS", "0001", "SY0001.BIN")
ff = recom_ffmw.parse(open(os.path.join(R, f"UK_{kind}font.binl"), "rb").read())
W = ff["widths"]
cell = 20 if kind == "sys" else 26


def line_widths(m):
    out, w = [], 0
    i = 0
    while i < len(m):
        c = m[i]
        if c == 0x0A:
            out.append(w); w = 0; i += 1; continue
        if c >= 0x80:
            code = (c << 8) | (m[i + 1] if i + 1 < len(m) else 0)
            i += 2
            if c in (0xF5, 0xF6):          # 아이콘: 칸 폭 하나로 침 (추정)
                w += cell; continue
            if c == 0xF9:                  # 색: 폭 없음
                continue
        else:
            code = c; i += 1
            if c < 0x20:
                continue
        try:
            g = ff["map"][fg.code_index(code)]
            w += W[g] if g < len(W) else cell
        except (ValueError, IndexError):
            w += cell
    out.append(w)
    return out


stats = collections.defaultdict(list)
over = []
for dp, dns, fns in os.walk(os.path.join(data, "remastered")):
    for f in fns:
        if not (f.startswith("UK_") and f.endswith(".ctdl")):
            continue
        b = open(os.path.join(dp, f), "rb").read()
        d = recom_ctd.parse(b)
        for k in range(d["n_lay"]):
            e = b[0x10 + 0x30 * k: 0x40 + 0x30 * k]
            start, cnt = struct.unpack_from("<H", e, 0x10)[0], struct.unpack_from("<H", e, 0x14)[0]
            size = struct.unpack_from("<H", e, 0x22)[0]
            msgs = d["msgs"][start:start + cnt]
            if not msgs or not size:
                continue
            mx = max(max(line_widths(m)) for m in msgs) * size / cell
            nl = max(len(line_widths(m)) for m in msgs)
            for off in (0x16, 0x18, 0x1A, 0x1C):
                v = struct.unpack_from("<H", e, off)[0]
                if v:
                    stats[off].append(mx / v)
            fw = struct.unpack_from("<H", e, 0x1A)[0]
            if fw and mx > fw * 1.02:
                over.append((os.path.relpath(os.path.join(dp, f), data), k, round(mx), fw, nl, recom_ctd.show(max(msgs, key=lambda m: max(line_widths(m))))[:70]))
for off, v in stats.items():
    v.sort()
    n = len(v)
    print(f"+{off:02X}: n={n} 비율(최대줄폭/필드) p50 {v[n // 2]:.2f} p90 {v[int(n * .9)]:.2f} p99 {v[int(n * .99)]:.2f} max {v[-1]:.2f}  >1.02: {sum(x > 1.02 for x in v)}")
print("+1A 보다 넓은 원문 줄:", len(over))
for o in over[:15]:
    print(" ", o)
