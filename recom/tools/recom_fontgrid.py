"""글꼴 png 격자 측정 + UK 텍스트가 쓰는 글리프 집계.

사용: python recom_fontgrid.py <Recom 추출 폴더> <sys|evt>
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import recom_ctd, recom_ffmw


def code_index(code):
    """문자 코드 -> FFMW 표 칸 `확정` (exe 0x25C480 의 역변환, PoC 3).
    1바이트: code-0x20.  2바이트: lead 0x81~0x84 -> 96 + (lead-0x81)*192 + (trail-0x40)
                                lead 0x87~0x9F -> 864 + (lead-0x87)*192 + (trail-0x40)   (0x85, 0x86 은 없음)
                                lead 0xE0~     -> 5664 + (lead-0xE0)*192 + (trail-0x40)"""
    if code < 0x100:
        return code - 0x20
    lead, trail = code >> 8, code & 0xFF
    if 0x81 <= lead <= 0x84:
        base = 96 + (lead - 0x81) * 192
    elif 0x87 <= lead <= 0x9F:
        base = 864 + (lead - 0x87) * 192
    elif lead >= 0xE0:
        base = 5664 + (lead - 0xE0) * 192
    else:
        raise ValueError(f"표에 없는 첫 바이트: {code:04X}")
    return base + (trail - 0x40)


def index_code(i):
    """code_index 의 역 (exe 0x25C480 과 같은 규칙)."""
    if i < 0x60:
        return i + 0x20
    i -= 0x60
    if i < 0x300:
        lead = 0x81
    else:
        i -= 0x300
        if i < 0x12C0:
            lead = 0x87
        else:
            i -= 0x12C0
            lead = 0xE0
    return ((lead + i // 192) << 8) | (i % 192 + 0x40)


# 글리프 칸 위치 `확정` (exe 0x25C2DB: 열 = PS2 폭 / 칸, 행 = PS2 높이 / 칸, 페이지 = 열 x 행; HD = PS2 x 2, 페이지는 2x2)
LAYOUT = {"sys": dict(cell=40, cols=25, rows=12, page_w=1024, page_h=512),
          "evt": dict(cell=52, cols=19, rows=19, page_w=1024, page_h=1024)}


def cell_xy(kind, g):
    L = LAYOUT[kind]
    per = L["cols"] * L["rows"]
    p, r, c = g // per, (g % per) // L["cols"], g % L["cols"]
    return (p % 2) * L["page_w"] + c * L["cell"], (p // 2) * L["page_h"] + r * L["cell"]


CTRL2 = (0xF5, 0xF6, 0xF9)    # 2바이트 제어: {F5}x {F6}x 아이콘, {F9}x 색 (exe 0x25AF4F 에서 F9 인자 분기 확인)


def codes(msg):
    """글자 코드만 (제어 코드 F5/F6/F9 + 인자는 건너뜀).
    디코더 규칙 `확정` (exe 0x258EB0/0x258F20): 0x80 이상 바이트는 항상 2바이트, 0x20 이하는 제어(줄바꿈 0x0A 등)."""
    i = 0
    while i < len(msg):
        c = msg[i]
        if c >= 0x80:
            if c not in CTRL2 and i + 1 < len(msg):
                yield (c << 8) | msg[i + 1]
            i += 2
        else:
            yield c
            i += 1


def occupancy(png, axis):
    im = Image.open(png).getchannel("A")
    w, h = im.size
    px = im.load()
    if axis == 0:
        return [sum(1 for y in range(0, h, 2) if px[x, y] > 16) for x in range(w)]
    return [sum(1 for x in range(0, w, 2) if px[x, y] > 16) for y in range(h)]


def gaps(occ):
    """잉크가 없는 구간의 중심들."""
    out, s = [], None
    for i, v in enumerate(occ + [1]):
        if v == 0 and s is None:
            s = i
        elif v and s is not None:
            out.append((s + i - 1) / 2)
            s = None
    return out


if __name__ == "__main__":
    root, kind = sys.argv[1], sys.argv[2]
    vt = os.path.join(root, "remastered", "SYS", "0001")
    png = os.path.join(vt, "SY0001.VTM", f"UK_{kind}font_fo240.png")
    ff = recom_ffmw.parse(open(os.path.join(vt, "SY0001.BIN", f"UK_{kind}font.binl"), "rb").read())
    for ax, name in ((0, "열"), (1, "행")):
        g = gaps(occupancy(png, ax))
        d = [round(b - a, 1) for a, b in zip(g, g[1:])]
        print(f"{name} 빈 구간 {len(g)}개, 간격 앞부분 {d[:30]}")
    used = {}
    for dp, dns, fns in os.walk(os.path.join(root, "remastered")):
        for f in fns:
            if f.startswith("UK_") and f.endswith(".ctdl"):
                for m in recom_ctd.parse(open(os.path.join(dp, f), "rb").read())["msgs"]:
                    for c in codes(m):
                        if c >= 0x20:
                            used[c] = used.get(c, 0) + 1
    gl = set()
    bad = []
    for c in used:
        i = code_index(c)
        if 0 <= i < len(ff["map"]):
            gl.add(ff["map"][i])
        else:
            bad.append(c)
    print(f"UK 텍스트 코드 {len(used)}종 (2바이트 {sum(1 for c in used if c > 0xFF)}), 쓰는 글리프 {len(gl)}개, 표 밖 코드 {[hex(c) for c in bad][:20]}")
    print("2바이트 코드:", " ".join(f"{c:04X}" for c in sorted(used) if c > 0xFF)[:600])
    allg = set(v for v in ff["map"] if v)
    print(f"표가 가리키는 글리프 {len(allg)}개, 최대 {max(allg)}; 표에 있지만 UK 텍스트가 안 쓰는 글리프 {len(allg - gl)}개")
