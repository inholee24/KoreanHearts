"""이미 찍은 게임 화면에서 글자 전진·공백 폭을 재서 공백 규칙(3/8, 1/2, 15/18 x 크기)을 고른다 (게임 실행 없음).

입력: 화면 캡처 png, 글줄 영역 (x0 y0 x1 y1), 그 줄의 원문 문자열 (영문, 공백 포함), 글자 크기(레이아웃 +0x22).
방법: 열마다 잉크 유무 -> 잉크 덩어리 = 글자. 단어 사이 큰 틈으로 단어를 나누고, 단어 시작 x 를 원문 폭 표로 예측한
      위치와 맞춰 최소제곱으로 (화면 배율, 공백 폭)을 구한다.
사용: python -I recom_measure_space.py <png> x0 y0 x1 y1 "<원문>" <크기>
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import recom_font, recom_paths as P

png = sys.argv[1]
x0, y0, x1, y1 = map(int, sys.argv[2:6])
text, size = sys.argv[6], int(sys.argv[7])
im = Image.open(png).convert("RGB").crop((x0, y0, x1, y1))
px = im.load()
W, H = im.size
ink = [any(max(px[x, y]) > 150 for y in range(H)) for x in range(W)]
runs, s = [], None
for x, v in enumerate(ink + [False]):
    if v and s is None:
        s = x
    elif not v and s is not None:
        runs.append((s, x)); s = None
gaps = sorted(b[0] - a[1] for a, b in zip(runs, runs[1:]))
thr = (max(gaps) + sorted(gaps)[len(gaps) // 2]) / 2
words_x = [runs[0][0]] + [b[0] for a, b in zip(runs, runs[1:]) if b[0] - a[1] > thr]
font = recom_font.Font("sys")
cell = 20
adv = []                       # 단어 시작 위치 예측: (글자 전진 합 PS2px, 공백 수)
acc, nsp = 0.0, 0
starts = [(0.0, 0)]
for ch in text:
    if ch == " ":
        nsp += 1
        starts.append((acc, nsp))
        continue
    g = font.glyph_of(ord(ch))
    acc += font.width(g) * size / cell
starts = starts[:len(words_x)]
# words_x[k] - words_x[0] = scale * (letters_k + nsp_k * sp)  -> 최소제곱 (scale, scale*sp)
import itertools
A = [(l, n) for l, n in starts]
Y = [wx - words_x[0] for wx in words_x]
sxx = sum(l * l for l, n in A); sxn = sum(l * n for l, n in A); snn = sum(n * n for l, n in A)
sxy = sum(l * y for (l, n), y in zip(A, Y)); sny = sum(n * y for (l, n), y in zip(A, Y))
det = sxx * snn - sxn * sxn
a = (sxy * snn - sny * sxn) / det
b = (sxx * sny - sxn * sxy) / det
sp = b / a
print(f"글자 덩어리 {len(runs)}, 단어 {len(words_x)}, 화면 배율 {a:.3f} px/PS2px, 공백 {sp:.2f} PS2px (크기 {size})")
for name, v in (("3/8", size * 3 / 8), ("1/2", size / 2), ("15/18", size * 15 / 18)):
    print(f"  후보 {name}: {v:.2f}  차이 {abs(v - sp):.2f}")
