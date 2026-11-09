"""Re:COM 그림 IMGZ/IMGD (.imz) 읽기·쓰기 (file-formats.md "그림 IMGZ / IMGD").

load(path_or_bytes) -> (raw bytes, [ (w, h, RGBA PIL.Image) ... ])   알파는 원본 그대로 (0~128)
save(raw, images) -> bytes   같은 크기 그림의 픽셀만 바꿔 쓴다 (머리말·순서 그대로)
사용: python -I recom_imz.py <imz> [png 폴더]   (그림을 png 로 풀기; 알파 x2 로 보기 좋게)
"""
import os, struct, sys
from PIL import Image


def _entries(b):
    assert b[:4] == b"IMGZ", "IMGZ 아님"
    n = struct.unpack_from("<I", b, 0xC)[0]
    out = []
    for i in range(n):
        off, ln = struct.unpack_from("<II", b, 0x10 + 8 * i)
        d = b[off:off + ln]
        assert d[:4] == b"IMGD"
        po, pl = struct.unpack_from("<II", d, 8)
        w, h = struct.unpack_from("<HH", d, 0x1C)
        fmt = struct.unpack_from("<H", d, 0x32)[0]
        assert fmt == 19 and pl == w * h * 4, f"지원 안 하는 형식 {fmt}"
        out.append((off + po, w, h))
    return out


def load(src):
    b = open(src, "rb").read() if isinstance(src, str) else bytes(src)
    return b, [(w, h, Image.frombytes("RGBA", (w, h), b[o:o + w * h * 4])) for o, w, h in _entries(b)]


def save(raw, images):
    out = bytearray(raw)
    for (o, w, h), im in zip(_entries(raw), images):
        assert im.size == (w, h) and im.mode == "RGBA"
        out[o:o + w * h * 4] = im.tobytes()
    return bytes(out)


def preview(im):
    """알파 0~128 -> 0~255 로 늘려 검은 바탕에 합성 (보기용)."""
    a = im.getchannel("A").point(lambda v: min(255, v * 2))
    v = im.copy(); v.putalpha(a)
    bg = Image.new("RGBA", im.size, (0, 0, 0, 255)); bg.alpha_composite(v)
    return bg.convert("RGB")


if __name__ == "__main__":
    raw, ims = load(sys.argv[1])
    if load(sys.argv[1])[0] != save(raw, [im for _, _, im in ims]):
        sys.exit("왕복 다름")
    print("그림", len(ims), [(w, h) for w, h, _ in ims], "왕복 같음")
    if len(sys.argv) > 2:
        os.makedirs(sys.argv[2], exist_ok=True)
        for i, (_, _, im) in enumerate(ims):
            preview(im).save(os.path.join(sys.argv[2], f"{os.path.basename(sys.argv[1])}.{i}.png"))
