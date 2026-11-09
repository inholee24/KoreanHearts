"""설정 메뉴 (Image/SettingMenu.pkg) 한글 적용 (45차).

  python tools/settingmenu.py           확인만
  python tools/settingmenu.py --apply   mod/kh1/uk/ctd/ct00100.ctd, mod/kh1/uk/font/menufont.{inf,cod,tm2} 에 쓴다

원본: D:/Projects/openkh_extract/SettingMenu/original (IdxImg hed extract). Panacea 가 mod/kh1/uk/... 로 교체함을 45차에 확인.
번역: translation/settingmenu.tsv (key = flags:id, en/ko 는 ctd.show 형식: {E3D0} 아이콘, \\n 줄바꿈).

글꼴 menufont (uk/font, 바이트로 확인):
  .inf 16B: u16 글자 수, u16 텍스처 폭 2048, u16 높이 2048, u8 칸 폭 32, u8 칸 높이 32, 나머지 CD
  .cod 8B 씩: u16 유니코드, u16 x, u16 y, u8 0, u8 전진 폭 (영문 6~25, 한자 28)
  .tm2 TIM2: 헤더 0x40, 2048x2048 RGBA 32bpp, RGB 흰색, 알파 0~128 (PS2 식)
  원본은 y < 384 (12줄) 만 쓴다 -> 한글은 y=384 부터 64칸씩.
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import ctd

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "data", "settingmenu")
MOD = os.path.join(ROOT, "mod", "kh1")
TSV = os.path.join(ROOT, "translation", "settingmenu.tsv")
CTD_REL = "uk/ctd/ct00100.ctd"
FONT_REL = "uk/font/menufont"
TTF = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_PX = 24
BASELINE = 27          # 칸 위에서 기준선까지 (영문 대문자 9~27 줄, 한자 6~30 줄)
ADV = 24               # 한글 전진 폭 (한자 28). 46차 27 은 글자 사이가 넓어 보였다 -> 24 (글자 폭 약 23)
CELL, SIZE, Y0 = 32, 2048, 384


def unshow(s):
    out, i = [], 0
    s = s.replace("\\n", "\n")
    while i < len(s):
        if s[i] == "{" and s[i + 5:i + 6] == "}":
            out.append(chr(int(s[i + 1:i + 5], 16))); i += 6
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def read_tsv():
    rows = {}
    for ln in open(TSV, encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            k, en, ko = ln.split("\t")
            rows[k] = (en, ko)
    return rows


def render(font, ch):
    m = Image.new("L", (CELL, CELL), 0)
    ImageDraw.Draw(m).text((ADV / 2, BASELINE), ch, font=font, fill=255, anchor="ms")
    cell = Image.new("RGBA", (CELL, CELL), (255, 255, 255, 0))
    cell.putalpha(m.point(lambda v: (v * 128 + 127) // 255))
    return cell


def main(apply):
    b = open(os.path.join(SRC, CTD_REL), "rb").read()
    d = ctd.parse(b)
    rows = read_tsv()
    texts, n, bad = [], 0, []
    for m in d["msgs"]:
        k = f"{m['flags']:04x}:{m['id']:04x}"
        t = m["text"]
        if k in rows and rows[k][1]:
            if rows[k][0] != ctd.show(t):
                bad.append(k)
            else:
                t = unshow(rows[k][1]); n += 1
        texts.append(t)
    if bad:
        sys.exit(f"원문 불일치: {bad}")
    used = set(rows) - {f"{m['flags']:04x}:{m['id']:04x}" for m in d["msgs"]}
    if used:
        sys.exit(f"없는 키: {sorted(used)}")

    inf = bytearray(open(os.path.join(SRC, FONT_REL + ".inf"), "rb").read())
    cod = open(os.path.join(SRC, FONT_REL + ".cod"), "rb").read()
    tm2 = bytearray(open(os.path.join(SRC, FONT_REL + ".tm2"), "rb").read())
    cnt = struct.unpack_from("<H", inf, 0)[0]
    recs = [cod[i:i + 8] for i in range(0, cnt * 8, 8)]
    have = {struct.unpack_from("<H", r, 0)[0] for r in recs}
    if max(struct.unpack_from("<H", r, 4)[0] for r in recs) >= Y0:
        sys.exit("원본 글꼴이 y>=384 를 이미 씀")
    orig = {c for m in d["msgs"] for c in m["text"]}           # 원문에 이미 있는 글자 (글꼴에 없어도 원래 그대로)
    need = sorted({c for t in texts for c in t if ord(c) not in have and c not in orig and c != "\n"})
    nonhangul = [c for c in need if not "\uac00" <= c <= "\ud7a3"]
    print(f"번역 {n}줄 / 메시지 {len(texts)}, 새 글자 {len(need)} (한글 외 {nonhangul})")
    if not apply:
        return
    im = Image.frombytes("RGBA", (SIZE, SIZE), bytes(tm2[0x40:0x40 + SIZE * SIZE * 4]))
    font = ImageFont.truetype(TTF, FONT_PX)
    for k, ch in enumerate(need):
        x, y = (k % (SIZE // CELL)) * CELL, Y0 + (k // (SIZE // CELL)) * CELL
        im.paste(render(font, ch), (x, y))
        recs.append(struct.pack("<HHHBB", ord(ch), x, y, 0, ADV))
    tm2[0x40:0x40 + SIZE * SIZE * 4] = im.tobytes()
    struct.pack_into("<H", inf, 0, len(recs))
    newcod = b"".join(recs)
    newcod += b"\xCD" * (-len(newcod) % 16)
    out = {CTD_REL: ctd.build(d, texts), FONT_REL + ".inf": bytes(inf), FONT_REL + ".cod": newcod,
           FONT_REL + ".tm2": bytes(tm2)}
    for rel, data in out.items():
        p = os.path.join(MOD, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(data)
        print("썼음", rel, len(data))


if __name__ == "__main__":
    main("--apply" in sys.argv)
