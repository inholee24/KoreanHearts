"""시스템(UI) 글꼴 한글 적용: exchange/US_font_data_tbl.bin + remastered/menu/uk/sysfont.bin/UK_sysfont_bin0.dds (40차).

exe 근거 (docs/exe-analysis.md 'UI 글꼴'):
  표   레코드 16B: +2 X, +4 Y (1/16 PS2px), +6 폭(u8, 전진량이자 소스 폭), +7 페이지(하위 니블 CSA, 상위 니블 0=4HL 1=4HH),
       +8 유니코드. 정적 버퍼 0x2E16BF0 은 0x4000B = 1024 레코드 (다음 전역 0x2E1ABF0). 원본 파일은 560개.
  그리기 0x2CFBF0: 소스 사각형 = (X, Y) ~ (X + 폭*16, Y + [0x545344]*16), [0x545344] = 24 (실행 중 값)
  HD 변환 0x304483: CSA==1 이면 u += 0x1000, PSM==4HH 이면 v += 0x1000, 그다음 hd = (2*값 - 8)/16 픽셀
  정규화: 텍스처 논리 크기 +0x94 로 나눔. sysfont 로더 0x2D18F0 이 +0x94 = +0x7C (= DDS 실제 크기) 로 둔다
  -> DDS 를 2048 로 키우면 기존 좌표는 왼쪽 위 1024 에 1:1, 그 밖은 새 좌표로 쓸 수 있다.
  메시지 코드: 0x20 이상 1바이트 = idx+0x20, 0x15~0x1F(0x18 제외) 2바이트 = (b0<<8|b1)-0x1820. 대화창과 달리 0x1A 도 됨.

글자 칸: 영어판에서 쓰지 않는 레코드(가나, 전각 공백) 중 idx>=256 은 제자리 칸을 지우고 다시 그린다.
새 레코드 560~1023 은 확장 영역(오른쪽 위 x>=1024, 아래쪽 y>=1024) 에 칸을 만든다. 2바이트 둘째 바이트 00/04 는 뺀다.
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import knj_tex1024 as kt

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "kh1")
TBL_REL = "exchange/US_font_data_tbl.bin"
DDS_REL = "remastered/menu/uk/sysfont.bin/UK_sysfont_bin0.dds"
N_REC = 2016                     # 2바이트 코드 최대 (0x1FFF - 0x1820 = 2015). 43차
FILE_REC = 1024                  # 게임이 읽는 표 파일 = 정적 버퍼 0x2E16BF0 (0x4000B). 그 뒤는 mem.py 가 붙인다
FULL_OUT = os.path.join(ROOT, "translation", "build", "sysfont_tbl_full.bin")   # mem.py tex2x 가 게임 메모리에 올리는 전체 표
SIZE = 2048
CELL_W, CELL_H = 36, 48          # HD px (PS2 18 x 24)
HANGUL_W = 16                    # +6 폭 (전각 가나와 같음). 소스 폭 = 32 HD px
FONT = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_PX = 31
GLYPH_BOTTOM = 38                # 칸 위에서 기준선까지. 한글 11~41 줄 = 영문 대문자 12~40 줄 (41차: 43 이면 월드맵 녹색 선에 아래가 가려짐)
COLOR = (0x82, 0x82, 0x81)       # 원본 글자 RGB. 알파 = 커버리지, 테두리 없음


def rec_uv(r):
    """레코드 -> HD 칸 왼쪽 위 (정수 px). 0x304483 의 변환."""
    X, Y, _, pg = struct.unpack_from("<HHBB", r, 2)
    X += 0x1000 if pg & 0xF == 1 else 0
    Y += 0x1000 if pg >> 4 == 1 else 0
    return (2 * X - 8) // 16, (2 * Y - 8) // 16


def usable(idx):
    # 480~735 (첫 바이트 0x1A) 제외 (44차). 지미니 메모에서 이 글자들이 빠졌는데, 나중에 본문이 대화창 글꼴로
    # 그려진 탓으로 밝혀졌다 (evmsg_export SHARED_FILES 주석). 시스템 글꼴 자체의 0x1A 문제는 확인되지 않았으나
    # 칸이 남아 그대로 둔다.
    return idx >= 256 and not 480 <= idx < 736 and (idx + 0x20) & 0xFF not in (0x00, 0x04)


def sjis_code(idx):
    """allarea.nam 같은 Shift-JIS 문자열에서 이 레코드를 찾을 가짜 2바이트 코드 (레코드 +0..1, 42차).
    첫 바이트 F0~FF 는 원본 표에 없고, 둘째 바이트 80~FF 라 00(끝)·0A 와 겹치지 않는다."""
    return bytes([0xF0 + (idx >> 7), 0x80 + (idx & 0x7F)])


def code(idx):
    return bytes([idx + 0x20]) if idx < 224 else (idx + 0x1820).to_bytes(2, "big")


def pool(tbl, base_alpha):
    """(idx, (x, y), 제자리 여부) 목록. 확장 오른쪽/아래/제자리를 번갈아 써서 세 경로가 모두 쓰이게 한다."""
    inplace = []
    for i in range(256, 560):
        r = tbl[i * 16:i * 16 + 16]
        cp = struct.unpack_from("<H", r, 8)[0]
        if not usable(i) or not (cp == 0x3000 or 0x3040 <= cp <= 0x30FF):
            continue
        x, y = rec_uv(r)
        if cp == 0x3000 and base_alpha.crop((x, y, x + CELL_W, y + CELL_H)).getbbox():
            continue                                  # 빈 레코드인데 칸에 그림이 있으면 건드리지 않음
        inplace.append((i, (x, y), True))
    right = [(x, y) for y in range(0, 21 * CELL_H, CELL_H) for x in range(1024, SIZE - CELL_W + 1, CELL_W)]
    bottom = [(x, y) for y in range(1024, 1024 + 21 * CELL_H, CELL_H) for x in range(0, SIZE - CELL_W + 1, CELL_W)]
    new_idx = [i for i in range(560, N_REC) if usable(i)]
    ext = []
    ri = bi = 0
    for k, i in enumerate(new_idx):               # 오른쪽/아래를 번갈아, 한쪽이 다 차면 다른 쪽
        if (k % 2 == 0 and ri < len(right)) or bi >= len(bottom):
            ext.append((i, right[ri], False)); ri += 1
        else:
            ext.append((i, bottom[bi], False)); bi += 1
    hi = [e for e in ext if e[0] >= FILE_REC]          # 표 파일 밖 (mem.py 패치가 있어야 보임) 은 맨 뒤
    ext = [e for e in ext if e[0] < FILE_REC]
    out, a, b = [], 0, 0
    while a < len(ext) or b < len(inplace):           # 확장 2 : 제자리 1
        for _ in range(2):
            if a < len(ext):
                out.append(ext[a]); a += 1
        if b < len(inplace):
            out.append(inplace[b]); b += 1
    return out + hi


def render(font, ch):
    m = Image.new("L", (CELL_W, CELL_H), 0)
    ImageDraw.Draw(m).text((HANGUL_W, GLYPH_BOTTOM), ch, font=font, fill=255, anchor="ms")
    cell = Image.new("RGBA", (CELL_W, CELL_H), COLOR + (0,))
    cell.putalpha(m)
    return cell


def _load():
    tbl = bytearray(open(os.path.join(DATA, TBL_REL), "rb").read())
    hdr, base = kt.read_dds(os.path.join(DATA, DDS_REL))
    if base.size != (1024, 1024) or len(tbl) != 560 * 16:
        sys.exit("원본 sysfont DDS/표 크기가 예상과 다름")
    tbl += tbl[139 * 16:140 * 16] * (N_REC - 560)    # 전각 공백 레코드 (폭 1) 로 늘림
    return tbl, hdr, base


def slot_indices():
    """배정 순서대로 쓸 수 있는 idx 목록 (build 가 쓰는 순서와 같음)."""
    tbl, _, base = _load()
    return [i for i, _, _ in pool(tbl, base.split()[3])]


def build(chars, fixed=None):
    """chars: 많이 쓰인 순서의 글자 목록. fixed: {글자: idx} 정해진 칸 (대화창 글꼴과 같은 코드를 쓰는 공유 글자, 42차).
    돌려줌: (표 bytes, DDS 헤더, DDS 이미지, {글자: 코드 bytes}, [(글자, idx, x, y)])"""
    fixed = fixed or {}
    tbl, hdr, base = _load()
    allslots = pool(tbl, base.split()[3])
    by_idx = {s[0]: s for s in allslots}
    rest = [s for s in allslots if s[0] not in set(fixed.values())]
    free = [c for c in chars if c not in fixed]
    if len(free) > len(rest):
        sys.exit(f"시스템 글꼴 글자 {len(free)}개 > 남은 칸 {len(rest)}개 (공유 {len(fixed)}개 별도)")
    pairs = [(c, by_idx[i]) for c, i in fixed.items()] + list(zip(free, rest))
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    img.paste(base, (0, 0))
    font = ImageFont.truetype(FONT, FONT_PX)
    gbytes, placed = {}, []
    for ch, (i, (x, y), inplace) in pairs:
        img.paste(render(font, ch), (x, y))           # 제자리 칸도 통째로 덮어 원래 가나를 지운다
        r = bytearray(16)
        r[0:2] = sjis_code(i)
        if inplace:
            r[2:6] = tbl[i * 16 + 2:i * 16 + 6]
            r[7] = tbl[i * 16 + 7]
        else:
            struct.pack_into("<HH", r, 2, x * 8 + 8, y * 8 + 8)   # hd = (2*X - 8)/16 -> X = 8*hd + 4, 원본처럼 +0.5
            r[7] = 0
        r[6] = HANGUL_W
        struct.pack_into("<H", r, 8, ord(ch))
        tbl[i * 16:i * 16 + 16] = r
        gbytes[ch] = code(i)
        placed.append((ch, i, x, y))
    return bytes(tbl), hdr, img, gbytes, placed


if __name__ == "__main__":
    # 확인용: 표본 글자로 칸 수와 위치만 출력
    t0 = bytearray(open(os.path.join(DATA, TBL_REL), "rb").read())
    t0 += t0[139 * 16:140 * 16] * (N_REC - 560)
    sl = pool(t0, kt.read_dds(os.path.join(DATA, DDS_REL))[1].split()[3])
    print(f"칸 {len(sl)} (제자리 {sum(s[2] for s in sl)}, 확장 {sum(not s[2] for s in sl)})")
    t, h, im, gb, pl = build(list("가나다라마바사아자차카타파하"))
    print(f"표 {len(t)}B, DDS {im.size}")
    for p in pl:
        print(p, gb[p[0]].hex())
