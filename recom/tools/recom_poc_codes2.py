"""PoC 3c: (1) 2바이트 매핑 변경이 적용되는가 (2) 한자 lead 코드가 이 표를 읽기는 하는가.

- 82A0 -> 700 '라' (원래 200)          : '라' 면 2바이트 매핑 변경 적용
- 82A2 그대로 201, 칸 201 에 '나'        : 대조
- 영어 텍스트가 쓰지 않는 표 칸 전부 -> 703 '아'
- 메시지: 82A0 82A2 889F 8970 9040 E040 + " Please..."
  기대: "라나아아아아" = 표 안 어딘가를 읽음 / 한자 자리 □ = 이 표를 안 읽음
사용: python recom_poc_codes2.py <Recom 추출 폴더> <mod\\recom> [--remove]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import recom_ctd, recom_fontgrid as fg, recom_poc3 as p3

SYS = "remastered/SYS/0001"
PNG = f"{SYS}/SY0001.VTM/UK_sysfont_fo240.png"
BINL = f"{SYS}/SY0001.BIN/UK_sysfont.binl"
CTDL = "remastered/FORM/0111/FO0111.CTD/UK_CT0005.ctdl"
CODES = [0x82A0, 0x82A2, 0x889F, 0x8970, 0x9040, 0xE040]


def used_codes(data):
    s = set()
    for dp, dns, fns in os.walk(os.path.join(data, "remastered")):
        for f in fns:
            if f.startswith("UK_") and f.endswith(".ctdl"):
                for m in recom_ctd.parse(open(os.path.join(dp, f), "rb").read())["msgs"]:
                    s.update(fg.codes(m))
    return s


def build(data):
    P = p3.PLAN["sys"]
    im = Image.open(os.path.join(data, *PNG.split("/"))).convert("RGBA")
    b = bytearray(open(os.path.join(data, *BINL.split("/")), "rb").read())
    mofs = struct.unpack_from("<H", b, 8)[0]
    n = (len(b) - mofs) // 2
    keep = {fg.code_index(c) for c in used_codes(data) if c >= 0x20}
    for g, ch in ((700, "라"), (201, "나"), (703, "아")):
        x, y = p3.cell_xy(P, g)
        gi, w = p3.glyph_img(P, ch)
        im.paste(Image.new("RGBA", (40, 40), (0, 0, 0, 0)), (x, y)); im.paste(gi, (x, y))
        b[0x10 + g] = w
    filled = 0
    for i in range(96, n):              # 2바이트 영역만 (1바이트 ASCII 는 그대로)
        if i not in keep:
            struct.pack_into("<H", b, mofs + 2 * i, 703); filled += 1
    struct.pack_into("<H", b, mofs + 2 * fg.code_index(0x82A0), 700)
    struct.pack_into("<H", b, mofs + 2 * fg.code_index(0x82A2), 201)
    print("채운 칸", filled, "유지", len(keep))
    raw = open(os.path.join(data, *CTDL.split("/")), "rb").read()
    d = recom_ctd.parse(raw)
    msgs = list(d["msgs"])
    msgs[29] = b"".join(c.to_bytes(2, "big") for c in CODES) + b" " + msgs[29]
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
