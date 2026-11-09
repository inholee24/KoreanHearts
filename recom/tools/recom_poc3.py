"""PoC 3: 매핑 표(binl) 교체, 새 칸 위치 (sysfont 1쪽·0쪽 마지막 행, evtfont 2·3쪽), 화면별 글꼴.

같은 한자 코드 3개를 두 글꼴에서 다른 칸·다른 한글로 연결한다.
  코드   sysfont 칸 -> 글자            evtfont 칸 -> 글자
  889F   200 (0쪽, あ 자리) -> 가        203 (0쪽, あ 자리) -> 다
  88A0   700 (1쪽)          -> 라        800 (2쪽, □ 영역)  -> 바
  88A1   620 (0쪽 마지막 행) -> 마        1100 (3쪽)        -> 사
화면에 "가라마" = sysfont, "다바사" = evtfont. 빠지거나 다른 글자 = 그 칸 위치 가설이 틀림.

글자 그리기는 원본 규칙을 따른다 (file-formats.md):
  sysfont: 흰색 + 알파, 테두리 없음, 칸 40, 글자 x=2 부터, 폭 1 = 2px
  evtfont: 회색(128) 채움 + 검정 테두리 + 알파, 칸 52
사용: python recom_poc3.py <Recom 추출 폴더> <mod\\recom> [--remove] [메시지 파일 rel:idx ...]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import recom_ctd, recom_fontgrid as fg

SYS = "remastered/SYS/0001"
FONT = r"C:\Windows\Fonts\malgunbd.ttf"
CODES = [0x889F, 0x88A0, 0x88A1]
PLAN = {
    "sys": dict(cell=40, cols=25, pages=(2, 1), glyphs=[200, 700, 620], text="가라마", size=32, outline=0, rgb=(255, 255, 255)),
    "evt": dict(cell=52, cols=19, pages=(2, 2), glyphs=[203, 800, 1100], text="다바사", size=40, outline=3, rgb=(128, 128, 128)),
}
MSGS = ["remastered/FORM/0111/FO0111.CTD/UK_CT0005.ctdl:29"]


def cell_xy(p, g):
    per = p["cols"] * p["cols"]
    page, r, c = g // per, (g % per) // p["cols"], g % p["cols"]
    return (page % p["pages"][0]) * 1024 + c * p["cell"], (page // p["pages"][0]) * 1024 + r * p["cell"]


def glyph_img(p, ch):
    n = p["cell"]
    font = ImageFont.truetype(FONT, p["size"])
    o = p["outline"]
    W = n
    fill = Image.new("L", (W, n)); edge = Image.new("L", (W, n))
    d = ImageDraw.Draw(fill)
    l, t, r, b = d.textbbox((0, 0), ch, font=font)
    x, y = 2 + o - l, (n - 4 - (b - t)) // 2 - t
    d.text((x, y), ch, font=font, fill=255)
    ImageDraw.Draw(edge).text((x, y), ch, font=font, fill=255, stroke_width=o, stroke_fill=255)
    out = Image.new("RGBA", (W, n), (0, 0, 0, 0))
    px, fp, ep = out.load(), fill.load(), edge.load()
    for yy in range(n):
        for xx in range(W):
            a = ep[xx, yy] if o else fp[xx, yy]
            if a:
                k = fp[xx, yy] / 255
                px[xx, yy] = tuple(int(c * k) for c in p["rgb"]) + (a,)
    width = (r - l + 2 * o + 4) // 2 + 1        # 폭 단위 (1 = 2px)
    return out, width


def build(data):
    out = {}
    for kind, p in PLAN.items():
        png = f"{SYS}/SY0001.VTM/UK_{kind}font_fo240.png"
        binl = f"{SYS}/SY0001.BIN/UK_{kind}font.binl"
        im = Image.open(os.path.join(data, *png.split("/"))).convert("RGBA")
        b = bytearray(open(os.path.join(data, *binl.split("/")), "rb").read())
        mofs = struct.unpack_from("<H", b, 8)[0]
        wend = struct.unpack_from("<H", b, 6)[0]
        for code, g, ch in zip(CODES, p["glyphs"], p["text"]):
            x, y = cell_xy(p, g)
            gi, w = glyph_img(p, ch)
            im.paste(Image.new("RGBA", (p["cell"], p["cell"]), (0, 0, 0, 0)), (x, y))
            im.paste(gi, (x, y))
            assert 0x10 + g < wend
            b[0x10 + g] = w
            struct.pack_into("<H", b, mofs + 2 * fg.code_index(code), g)
        out[png] = im
        out[binl] = bytes(b)
    for spec in MSGS:
        rel, idx = spec.rsplit(":", 1)
        raw = open(os.path.join(data, *rel.split("/")), "rb").read()
        d = recom_ctd.parse(raw)
        msgs = list(d["msgs"])
        msgs[int(idx)] = b"".join(c.to_bytes(2, "big") for c in CODES) + b" " + msgs[int(idx)]
        out[rel] = recom_ctd.build(raw, d, msgs)
    return out


if __name__ == "__main__":
    data, mod = sys.argv[1], sys.argv[2]
    extra = [a for a in sys.argv[3:] if ":" in a and not a.startswith("--")]
    MSGS += extra
    for rel, v in build(data).items():
        p = os.path.join(mod, *rel.split("/"))
        if "--remove" in sys.argv:
            if os.path.exists(p):
                os.remove(p); print("지움", p)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        v.save(p) if isinstance(v, Image.Image) else open(p, "wb").write(v)
        print("씀", rel)
