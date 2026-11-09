"""PoC 2: 영어 모드에서 2바이트 코드로 한글이 그려지는지.

UK_sysfont_fo240.png 의 あ(82A0, 글리프 200)·い(82A2, 201) 칸에 '가'·'나' 를 그리고,
FO0111 UK .ctdl 메시지 #29 앞에 82A0 82A2 를 넣는다. 결과는 mod 폴더.

칸 위치 (recom/docs/file-formats.md): 페이지 = g // 625, 행 = g % 625 // 25, 열 = g % 25,
x = 페이지*1024 + 열*40, y = 행*40, 40x40.

사용: python recom_poc_hangul.py <추출 원본 Recom 폴더> <mod\\recom 폴더> [--remove]
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
import recom_ctd, recom_ffmw, recom_fontgrid as fg

PNG = "remastered/SYS/0001/SY0001.VTM/UK_sysfont_fo240.png"
BINL = "remastered/SYS/0001/SY0001.BIN/UK_sysfont.binl"
CTDL = "remastered/FORM/0111/FO0111.CTD/UK_CT0005.ctdl"
PAIRS = [("あ", "가"), ("い", "나")]
FONT = r"C:\Windows\Fonts\malgunbd.ttf"


def cell(g):
    page, r, c = g // 625, (g % 625) // 25, g % 25
    return page * 1024 + c * 40, r * 40


def build(data):
    ff = recom_ffmw.parse(open(os.path.join(data, *BINL.split("/")), "rb").read())
    im = Image.open(os.path.join(data, *PNG.split("/"))).convert("RGBA")
    font = ImageFont.truetype(FONT, 32)
    codes = b""
    for jp, ko in PAIRS:
        code = jp.encode("cp932")
        g = ff["map"][fg.code_index(int.from_bytes(code, "big"))]
        x, y = cell(g)
        glyph = Image.new("RGBA", (40, 40), (255, 255, 255, 0))
        d = ImageDraw.Draw(glyph)
        l, t, r, b = d.textbbox((0, 0), ko, font=font)
        d.text(((40 - (r - l)) / 2 - l, (36 - (b - t)) / 2 - t), ko, font=font, fill=(255, 255, 255, 255))
        im.paste(glyph, (x, y))
        codes += code
    b = open(os.path.join(data, *CTDL.split("/")), "rb").read()
    d = recom_ctd.parse(b)
    msgs = list(d["msgs"])
    msgs[29] = codes + b" " + msgs[29]
    out = recom_ctd.build(b, d, msgs)
    assert recom_ctd.parse(out)["msgs"] == msgs
    return {PNG: im, CTDL: out}


if __name__ == "__main__":
    data, mod = sys.argv[1], sys.argv[2]
    for rel, v in build(data).items():
        p = os.path.join(mod, *rel.split("/"))
        if "--remove" in sys.argv:
            if os.path.exists(p):
                os.remove(p); print("지움", p)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if isinstance(v, Image.Image):
            v.save(p)
        else:
            open(p, "wb").write(v)
        print("씀", p)
