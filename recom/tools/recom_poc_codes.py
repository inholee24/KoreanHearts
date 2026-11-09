"""PoC 3b: 첫 바이트(lead)별로 2바이트 코드가 매핑 표 공식대로 쓰이는지 (sysfont, 메뉴 화면).

코드마다 다른 글리프 칸에 다른 한글을 그리고 매핑 표(binl)에 연결한 뒤, FO0111 #29 앞에 모두 넣는다.
화면에 빠지거나 □ 로 나오는 글자의 코드는 공식이 맞지 않는 lead.
사용: python recom_poc_codes.py <Recom 추출 폴더> <mod\\recom> [--remove]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import recom_ctd, recom_fontgrid as fg, recom_poc3 as p3

TESTS = [(0x889F, 700, "라"), (0x8970, 905, "마"), (0x9040, 400, "바"), (0xE040, 1000, "사")]   # 칸 위치·공식은 recom_fontgrid (확정판)
EXTRA = [0x99A1]   # 기존 é (Naminé) 대조
SYS = "remastered/SYS/0001"
PNG = f"{SYS}/SY0001.VTM/UK_sysfont_fo240.png"
BINL = f"{SYS}/SY0001.BIN/UK_sysfont.binl"
CTDL = "remastered/FORM/0111/FO0111.CTD/UK_CT0005.ctdl"


def build(data):
    P = p3.PLAN["sys"]
    im = Image.open(os.path.join(data, *PNG.split("/"))).convert("RGBA")
    b = bytearray(open(os.path.join(data, *BINL.split("/")), "rb").read())
    mofs = struct.unpack_from("<H", b, 8)[0]
    for code, g, ch in TESTS:
        x, y = fg.cell_xy("sys", g)
        gi, w = p3.glyph_img(P, ch)
        im.paste(Image.new("RGBA", (40, 40), (0, 0, 0, 0)), (x, y))
        im.paste(gi, (x, y))
        b[0x10 + g] = w
        struct.pack_into("<H", b, mofs + 2 * fg.code_index(code), g)
    raw = open(os.path.join(data, *CTDL.split("/")), "rb").read()
    d = recom_ctd.parse(raw)
    msgs = list(d["msgs"])
    msgs[29] = b"".join(c.to_bytes(2, "big") for c in [t[0] for t in TESTS] + EXTRA) + b" " + msgs[29]
    return {PNG: im, BINL: bytes(b), CTDL: recom_ctd.build(raw, d, msgs)}


if __name__ == "__main__":
    data, mod = sys.argv[1], sys.argv[2]
    for rel, v in build(data).items():
        p = os.path.join(mod, *rel.split("/"))
        if "--remove" in sys.argv:
            if os.path.exists(p):
                os.remove(p); print("지움", p)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        v.save(p) if isinstance(v, Image.Image) else open(p, "wb").write(v)
        print("씀", rel)
