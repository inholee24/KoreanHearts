"""Re:COM 글꼴: 한글 글리프 그리기, 글꼴 png / FFMW 표 읽고 쓰기.

그림 규칙 (원본 측정, file-formats.md):
  sys: 칸 40, 흰색(255) + 알파 커버리지, 테두리 없음. 글자는 칸 왼쪽 x=2 부터. 맑은 고딕 Bold 32.
  evt: 칸 52, 회색(128) 채움 + 검정 테두리 + 알파 커버리지. 글자는 x=3 부터. 원본 영문 획이 가늘어 맑은 고딕 Regular 36 + 테두리 2.
  폭 표 값 1 = HD 2px. 원본 전각 가나 폭: sys 16~18, evt 18~20.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
import recom_ffmw, recom_fontgrid as fg, recom_paths as P

FONT_FILE = r"C:\Windows\Fonts\malgunbd.ttf"
STYLE = {
    "sys": dict(cell=40, size=32, stroke=0, rgb=(255, 255, 255), left=2, box_h=36, pad=3, file="malgunbd.ttf"),
    "evt": dict(cell=52, size=36, stroke=2, rgb=(128, 128, 128), left=3, box_h=47, pad=1, file="malgun.ttf"),
}


def png_rel(kind):
    return f"{P.SYS}/SY0001.VTM/UK_{kind}font_fo240.png"


def binl_rel(kind):
    return f"{P.SYS}/SY0001.BIN/UK_{kind}font.binl"


_fonts = {}


def render(kind, ch):
    """한 글자 -> (RGBA 칸 그림, 폭 표 값)."""
    st = STYLE[kind]
    n, o = st["cell"], st["stroke"]
    if kind not in _fonts:
        _fonts[kind] = ImageFont.truetype(os.path.join(os.path.dirname(FONT_FILE), st["file"]), st["size"])
    font = _fonts[kind]
    fill = Image.new("L", (n, n))
    d = ImageDraw.Draw(fill)
    l, t, r, b = d.textbbox((0, 0), ch, font=font)
    x = st["left"] + o - l
    y = (st["box_h"] - (b - t)) // 2 - t
    d.text((x, y), ch, font=font, fill=255)
    if o:
        edge = Image.new("L", (n, n))
        ImageDraw.Draw(edge).text((x, y), ch, font=font, fill=255, stroke_width=o, stroke_fill=255)
    else:
        edge = fill
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    px, fp, ep = out.load(), fill.load(), edge.load()
    for yy in range(n):
        for xx in range(n):
            a = ep[xx, yy]
            if a:
                k = fp[xx, yy] / 255
                px[xx, yy] = tuple(int(c * k) for c in st["rgb"]) + (a,)
    bb = out.getbbox()
    if bb and bb[0] != st["left"]:                # 잉크 왼쪽 끝을 원본 글자처럼 left 에 (글꼴 왼쪽 여백 제거)
        shifted = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        shifted.paste(out, (st["left"] - bb[0], 0))
        out = shifted
        bb = out.getbbox()
    right = bb[2] if bb else n // 2
    width = min(n // 2, (right + st["pad"] + 1) // 2)   # 원본 가나: sys 잉크 끝 = 2*폭-3, evt 잉크 끝 = 2*폭 (여백 없음)
    return out, width


class Font:
    """원본 글꼴(png + FFMW) 을 읽어 고친 뒤 쓴다."""

    def __init__(self, kind, data=None):
        data = data or P.DATA
        self.kind = kind
        self.img = Image.open(os.path.join(data, *png_rel(kind).split("/"))).convert("RGBA")
        self.raw = bytearray(open(os.path.join(data, *binl_rel(kind).split("/")), "rb").read())
        self.ff = recom_ffmw.parse(bytes(self.raw))
        self.mofs = self.ff["mofs"]

    def glyph_of(self, code):
        return struct.unpack_from("<H", self.raw, self.mofs + 2 * fg.code_index(code))[0]

    def set_map(self, code, g):
        struct.pack_into("<H", self.raw, self.mofs + 2 * fg.code_index(code), g)

    def set_width(self, g, w):
        assert 0x10 + g < self.ff["a"], f"폭 표 밖 글리프 {g}"
        self.raw[0x10 + g] = w

    def width(self, g):
        return self.raw[0x10 + g] if 0x10 + g < self.ff["a"] else 0

    def clear(self, g):
        n = STYLE[self.kind]["cell"]
        self.img.paste(Image.new("RGBA", (n, n), (0, 0, 0, 0)), fg.cell_xy(self.kind, g))

    def put(self, g, ch):
        cell, w = render(self.kind, ch)
        self.clear(g)
        self.img.paste(cell, fg.cell_xy(self.kind, g))
        self.set_width(g, w)
        return w

    def cell_img(self, g):
        n = STYLE[self.kind]["cell"]
        x, y = fg.cell_xy(self.kind, g)
        return self.img.crop((x, y, x + n, y + n))

    def save(self, mod):
        p = os.path.join(mod, *png_rel(self.kind).split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        self.img.save(p)
        q = os.path.join(mod, *binl_rel(self.kind).split("/"))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "wb").write(bytes(self.raw))
