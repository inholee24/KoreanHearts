"""대화창 글꼴 DDS(UK_kanji_knj0.dds)를 1024x1024 텍스처 배치로 다루는 도구.

배경 (docs/exe-analysis.md 5절): 영어판 대화창 글꼴 텍스처는 512x512 이고 페이지 0 만 담는다.
텍스처를 1024x1024 로 키우면 페이지 0~3 이 사분면이 된다 (비트0 -> 오른쪽, 비트1 -> 아래).
DDS 는 텍스처 전체에 늘여 붙으므로, 4096 DDS 기준 PS2 1px = 4px, 셀 24x32 -> 96x128.

사용 (openkh_venv python -I):
  convert <src512.dds> <dst1024.dds>          512 배치 DDS(어떤 정사각 크기든) -> 4096 의 왼쪽 위 2048 에 축소 배치
  copy <dds> <src_idx> <dst_idx> [...]          (1024 배치 DDS 안에서) 셀 복사, 쌍으로 여러 개
  width <knj> <dst_idx> <src_idx|=값> [...]     UK_kanji.knj 폭 표(0x40080+idx) 설정
  crop <dds> <idx> <out.png>                    셀 하나를 PNG 로 (확인용)
"""
import struct, sys
from PIL import Image

HDR = 128
SIZE = 4096
SCALE = SIZE // 1024          # PS2 px -> DDS px
CELL_W, CELL_H = 24, 32       # 영어 배치 (font_lang_setup 0x18D130)
COLS, ROWS = 21, 16
WIDTH_TBL = 0x40080


def read_dds(path):
    b = open(path, "rb").read()
    h, w = struct.unpack_from("<II", b, 12)
    if struct.unpack_from("<I", b, 88)[0] != 32 or b[84:88] != b"\0\0\0\0":
        sys.exit(f"{path}: 비압축 32bpp DDS 만 지원")
    return b[:HDR], Image.frombytes("RGBA", (w, h), b[HDR:HDR + w * h * 4])


def write_dds(path, hdr, img):
    w, h = img.size
    hdr = bytearray(hdr)
    struct.pack_into("<II", hdr, 12, h, w)
    struct.pack_into("<I", hdr, 20, w * 4)    # pitch
    open(path, "wb").write(bytes(hdr) + img.tobytes())


# 배치: en = 영어판 (16줄 x 32px, 1344칸), jp = 일본어판 (21줄 x 24px, 1764칸). 0x18D130 참조
LAYOUTS = {"en": {"rows": 16, "cell_h": 32, "count": 1344},
           "jp": {"rows": 21, "cell_h": 24, "count": 1764}}


def cell_box(idx, layout="en"):
    rows, cell_h = LAYOUTS[layout]["rows"], LAYOUTS[layout]["cell_h"]
    page, local = divmod(idx, COLS * rows)
    if page > 3:
        sys.exit(f"idx {idx}: 페이지 {page} 는 엔진이 처리하지 않음")
    row, col = divmod(local, COLS)
    x = ((page & 1) * 512 + col * CELL_W) * SCALE
    y = ((page >> 1) * 512 + row * cell_h) * SCALE
    return (x, y, x + CELL_W * SCALE, y + cell_h * SCALE)


def main(a):
    if not a:
        print(__doc__); return 2
    c = a[0]
    if c == "convert":
        hdr, img = read_dds(a[1])
        out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        out.paste(img.resize((SIZE // 2, SIZE // 2), Image.BOX), (0, 0))
        write_dds(a[2], hdr, out)
        print(f"{a[1]} {img.size} -> {a[2]} {out.size}, 페이지 0 = 왼쪽 위 {SIZE // 2}")
    elif c == "copy":
        hdr, img = read_dds(a[1])
        if img.size != (SIZE, SIZE):
            sys.exit(f"{img.size}: 1024 배치 DDS({SIZE}) 가 아님")
        for s, d in zip(a[2::2], a[3::2]):
            s, d = int(s, 0), int(d, 0)
            img.paste(img.crop(cell_box(s)), cell_box(d)[:2])
            print(f"cell {s} {cell_box(s)} -> {d} {cell_box(d)}")
        write_dds(a[1], hdr, img)
    elif c == "width":
        b = bytearray(open(a[1], "rb").read())
        for d, s in zip(a[2::2], a[3::2]):
            d = int(d, 0)
            v = int(s[1:], 0) if s.startswith("=") else b[WIDTH_TBL + int(s, 0)]
            print(f"width[{d}] {b[WIDTH_TBL + d]} -> {v}")
            b[WIDTH_TBL + d] = v
        open(a[1], "wb").write(b)
    elif c == "crop":
        _, img = read_dds(a[1])
        img.crop(cell_box(int(a[2], 0))).save(a[3])
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
