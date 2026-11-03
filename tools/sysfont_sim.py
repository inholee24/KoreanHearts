"""시스템(UI) 글꼴 렌더러 흉내 (40차): mod 의 표 + DDS 로 메시지를 그려 본다 (exe 규칙 그대로, 게임 없이 확인).
  디코드 0x2CFBF0: <0x15 제어(길이는 evmsg.code_len_ui, 42차), 0x18 건너뜀, 0x15~0x1F 2바이트, >=0x20 1바이트
  소스 0x2CFBF0/0x304483: u = 2*(X + CSA1*0x1000) - 8, v = 2*(Y + 4HH*0x1000) - 8 (1/16 HD px), 폭 = 2*+6, 높이 48
사용: python -I -X utf8 tools/sysfont_sim.py <출력.png> <데이터 상대경로> [메시지 번호...]
"""
import os, struct, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import evmsg, evmsg_export as ex, knj_tex1024 as kt, sysfont

MOD = os.path.join(ex.ROOT, "mod", "kh1")


def glyphs(m):
    i = 0
    while i < len(m):
        c = m[i]
        if c in (0x00, 0x04):
            return
        if c < 0x15 or c == 0x18:
            if c == 0x02:
                yield "nl"
            i += evmsg.code_len_ui(m, i)
            continue
        if c < 0x20:
            yield ((c << 8) | m[i + 1]) - 0x1820; i += 2
        else:
            yield c - 0x20; i += 1


def draw(m, tbl, tex):
    lines, cur = [], []
    for g in glyphs(m):
        if g == "nl":
            lines.append(cur); cur = []; continue
        X, Y, w, pg = struct.unpack_from("<HHBB", tbl, g * 16 + 2)
        u = (2 * (X + (0x1000 if pg & 0xF == 1 else 0)) - 8) // 16
        v = (2 * (Y + (0x1000 if pg >> 4 == 1 else 0)) - 8) // 16
        cur.append(tex.crop((u, v, u + 2 * w, v + 48)))
    lines.append(cur)
    W = max(sum(c.width for c in l) for l in lines) + 8
    out = Image.new("RGBA", (max(W, 8), 48 * len(lines) + 8), (30, 30, 80, 255))
    for k, l in enumerate(lines):
        x = 4
        for c in l:
            out.alpha_composite(c, (x, 4 + 48 * k)); x += c.width
    return out


def main(a):
    tbl = open(os.path.join(MOD, sysfont.TBL_REL), "rb").read()
    tex = kt.read_dds(os.path.join(MOD, sysfont.DDS_REL))[1]
    rel = a[1]
    msgs, refd = ex.messages(rel, open(os.path.join(MOD, rel), "rb").read(),
                             MOD if rel in ex.OFS_PAIRS else ex.DATA)
    pick = [int(x) for x in a[2:]] or sorted(refd)[:12]
    ims = [draw(msgs[i], tbl, tex) for i in pick]
    out = Image.new("RGBA", (max(i.width for i in ims), sum(i.height for i in ims)), (0, 0, 0, 255))
    y = 0
    for im in ims:
        out.paste(im, (0, y)); y += im.height
    out.convert("RGB").save(a[0])


if __name__ == "__main__":
    main(sys.argv[1:])
