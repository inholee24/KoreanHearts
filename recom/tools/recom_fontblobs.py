"""글꼴 png 에서 행 띠와 각 행의 글자 덩어리(x 범위)를 찾는다 (격자 규칙 추정용).
사용: python recom_fontblobs.py <png> [행수]"""
import sys
from PIL import Image

im = Image.open(sys.argv[1]).getchannel("A")
w, h = im.size
px = im.load()
rows_occ = [any(px[x, y] > 16 for x in range(0, w, 1)) for y in range(h)]
bands, s = [], None
for y, v in enumerate(rows_occ + [False]):
    if v and s is None:
        s = y
    elif not v and s is not None:
        bands.append((s, y - 1)); s = None
print(f"{w}x{h}, 행 띠 {len(bands)}개:", bands)
for (a, b) in bands[: int(sys.argv[2]) if len(sys.argv) > 2 else 4]:
    col = [any(px[x, y] > 16 for y in range(a, b + 1)) for x in range(w)]
    blobs, s = [], None
    for x, v in enumerate(col + [False]):
        if v and s is None:
            s = x
        elif not v and s is not None:
            blobs.append((s, x - 1)); s = None
    print(f"y {a}-{b}: {len(blobs)}개", [round((p + q) / 2) for p, q in blobs][:60])
