"""FFMW 폭 영역이 글리프 번호 순서인지: 폭 바이트와 png 칸의 잉크 폭 상관 (시작 오프셋 후보별).
사용: python recom_widthcheck.py <png> <binl> <칸크기> <페이지당 열> <페이지 폭> [행 높이]"""
import struct, sys
from PIL import Image

png, binl = sys.argv[1], sys.argv[2]
cw, cols, pw = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
ch = int(sys.argv[6]) if len(sys.argv) > 6 else cw
b = open(binl, "rb").read()
a = struct.unpack_from("<H", b, 6)[0]
A = Image.open(png).getchannel("A")
W, H = A.size
rows = H // ch
per_page = cols * rows
px = A.load()


def ink(g):
    page, r, c = g // per_page, (g % per_page) // cols, g % cols
    x0, y0 = page * pw + c * cw, r * ch
    if x0 + cw > W or y0 + ch > H:
        return None
    xs = [x for x in range(x0, x0 + cw) if any(px[x, y] > 64 for y in range(y0, y0 + ch))]
    return (xs[-1] - xs[0] + 1) if xs else 0


inks = {g: ink(g) for g in range(0, (a - 0x10))}
for start in (0x10, 0x12, 0x14, 0x18):
    pairs = [(b[start + g], inks[g]) for g in inks if inks[g] and start + g < a]
    n = len(pairs)
    mx = sum(p for p, _ in pairs) / n; my = sum(q for _, q in pairs) / n
    cov = sum((p - mx) * (q - my) for p, q in pairs)
    vx = sum((p - mx) ** 2 for p, _ in pairs) ** .5; vy = sum((q - my) ** 2 for _, q in pairs) ** .5
    print(f"start {start:#x}: n={n} r={cov / (vx * vy):.3f}  폭/잉크 비 중앙값 {sorted(q / p for p, q in pairs if p)[n // 2]:.2f}")
print("rows", rows, "per_page", per_page, "폭 바이트 수", a - 0x10)
