"""게임 규칙대로 메시지를 그려 보는 시뮬레이터 (게임 실행 없이 검토).

규칙 (file-formats.md): 코드 -> FFMW 매핑 -> 글리프 칸 (cell_xy), 전진 = 폭 표 값 x 2px, 줄바꿈 0x0A,
  0x80 이상 2바이트, [F9 x] 색 (그림에서는 색만 표시용으로 바꿈), [F5 x]/[F6 x] 아이콘 (칸 하나 자리 상자로 표시).
  크기 배율 = 레이아웃 +0x22 (글자 크기) / 칸 크기(sys 20, evt 26). 줄 간격 = 칸 높이 x 배율.
원문은 원본 글꼴, 번역은 mod 글꼴로 위아래에 그린다.

사용: python -I -X utf8 recom_sim.py <ctdl 상대 경로> [메시지 번호,...] [--font sys|evt] [--out png]
      (번호 생략 = 파일의 바뀐 메시지 전부, 최대 12)
출력 기본: translation/build/sim/<파일이름>.png
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
import recom_ctd, recom_font, recom_fontgrid as fg, recom_paths as P

CELL = {"sys": 20, "evt": 26}
SPACE = {k: v * 3 / 8 * 2 for k, v in CELL.items()}     # 공백 전진 HD px (칸 크기 x 3/8 PS2px x 2)
COLORS = {0x41: (255, 255, 255), 0x59: (255, 230, 90), 0x45: (150, 220, 255), 0x43: (255, 170, 120)}


def draw(font, msg, scale, color=(255, 255, 255)):
    """메시지 바이트 -> RGBA 그림 (HD px)."""
    n = recom_font.STYLE[font.kind]["cell"]
    lines, cur, i = [], [], 0
    while i < len(msg):
        c = msg[i]
        if c == 0x0A:
            lines.append(cur); cur = []; i += 1; continue
        if c >= 0x80:
            t = msg[i + 1] if i + 1 < len(msg) else 0
            i += 2
            if c == 0xF9:
                cur.append(("color", COLORS.get(t, (200, 200, 200)))); continue
            if c in (0xF5, 0xF6):
                cur.append(("icon", None)); continue
            code = (c << 8) | t
        else:
            i += 1
            if c == 0x20:                    # 공백: 크기 x 3/8 (exe 0x25AE87 분기, 게임 화면 측정 2건 6.49/5.56 vs 6.75)
                cur.append(("space", None)); continue
            if c < 0x20:
                continue
            code = c
        try:
            g = font.glyph_of(code)
        except ValueError:
            g = 0
        cur.append(("g", g))
    lines.append(cur)
    lh = int(n * scale)
    sp = SPACE[font.kind]

    def adv(x):
        return font.width(x[1]) * 2 if x[0] == "g" else sp if x[0] == "space" else n
    W = max(1, max(sum(adv(x) for x in ln if x[0] != "color") for ln in lines))
    out = Image.new("RGBA", (int(W * scale) + n, lh * len(lines) + 4), (0, 0, 0, 0))
    for li, ln in enumerate(lines):
        x, col = 0, color
        for kind, v in ln:
            if kind == "color":
                col = v; continue
            if kind == "space":
                x += sp; continue
            if kind == "icon":
                ImageDraw.Draw(out).rectangle([int(x * scale) + 2, li * lh + 4, int((x + n - 4) * scale), li * lh + lh - 4], outline=(120, 200, 120, 255))
                x += n; continue
            cell = font.cell_img(v)
            if col != (255, 255, 255) and font.kind == "sys":
                r, gch, b, a = cell.split()
                cell = Image.merge("RGBA", (r.point(lambda p: p * col[0] // 255), gch.point(lambda p: p * col[1] // 255), b.point(lambda p: p * col[2] // 255), a))
            cell = cell.resize((max(1, int(n * scale)), max(1, int(n * scale))), Image.BILINEAR)
            out.alpha_composite(cell, (int(x * scale), li * lh))
            x += font.width(v) * 2
    return out


def main(argv):
    rel = argv[0].replace("\\", "/")
    idxs = [int(x) for x in argv[1].split(",")] if len(argv) > 1 and not argv[1].startswith("--") else None
    kind = argv[argv.index("--font") + 1] if "--font" in argv else "sys"
    out_png = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(P.TR, "build", "sim", os.path.basename(rel) + f".{kind}.png")
    data, mod = P.DATA, P.MOD
    orig = open(os.path.join(data, rel), "rb").read()
    mp = os.path.join(mod, *rel.split("/"))
    cur = open(mp, "rb").read() if os.path.exists(mp) else orig
    do, dc = recom_ctd.parse(orig), recom_ctd.parse(cur)
    if idxs is None:
        idxs = [i for i, (a, b) in enumerate(zip(do["msgs"], dc["msgs"])) if a != b][:12] or list(range(min(6, len(do["msgs"]))))
    fo = recom_font.Font(kind, data)
    fm = recom_font.Font(kind, mod) if os.path.exists(os.path.join(mod, *recom_font.png_rel(kind).split("/"))) else fo
    size_of = {}
    for k in range(do["n_lay"]):
        e = orig[0x10 + 0x30 * k: 0x40 + 0x30 * k]
        s, c = struct.unpack_from("<H", e, 0x10)[0], struct.unpack_from("<H", e, 0x14)[0]
        for j in range(s, s + c):
            size_of[j] = (struct.unpack_from("<H", e, 0x22)[0], struct.unpack_from("<H", e, 0x1A)[0])
    tiles = []
    for i in idxs:
        size, boxw = size_of.get(i, (CELL[kind], 0))
        sc = (size or CELL[kind]) / CELL[kind]
        a = draw(fo, do["msgs"][i], sc)
        b = draw(fm, dc["msgs"][i], sc)
        tiles.append((i, size, boxw, a, b))
    W = max(max(a.width, b.width) for _, _, _, a, b in tiles) + 20
    H = sum(a.height + b.height + 30 for _, _, _, a, b in tiles)
    img = Image.new("RGBA", (W, H), (25, 30, 70, 255))
    d = ImageDraw.Draw(img)
    y = 0
    for i, size, boxw, a, b in tiles:
        d.text((4, y + 2), f"#{i} size {size} +1A {boxw}", fill=(160, 160, 160, 255))
        y += 14
        img.alpha_composite(a, (10, y)); y += a.height + 2
        d.line([(10, y), (W - 10, y)], fill=(70, 70, 110, 255))
        img.alpha_composite(b, (10, y + 2)); y += b.height + 14
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    img.save(out_png)
    print("그림:", out_png, f"{img.width}x{img.height}")


if __name__ == "__main__":
    main(sys.argv[1:])
