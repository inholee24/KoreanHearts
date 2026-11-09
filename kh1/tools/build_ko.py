"""번역 표(translation/kh1_evmsg.tsv) -> mod/kh1 대화창 한글 적용본 생성.

만드는 것 (원본 data/kh1 에서 새로 만든다. 이전 실험 상태에 의존하지 않음):
  remastered/exchange/UK_kanji.knj/UK_kanji_knj0.dds  4096x4096, 1024 텍스처 배치 (docs/exe-analysis.md 5절)
      페이지 0 = 원본 DDS(512 배치)를 2배 확대해 왼쪽 위 2048 에. 한글은 빈 칸에 맑은 고딕으로 그림.
  exchange/UK_kanji.knj   폭 표(0x40080+idx) 에 배정 글자 폭
  remastered/**/U[KS]_*.binl  번역이 있는 메시지를 바꾼 파일. 번역이 없어진 파일이 mod 에 남아 있으면 원본으로 되돌림
  translation/build/glyph_map.tsv  글자 -> idx/코드 (확인용)
  시스템 글꼴 (40차, tools/sysfont.py): exchange/US_font_data_tbl.bin (1024 레코드),
      remastered/menu/uk/sysfont.bin/UK_sysfont_bin0.dds (2048), translation/build/sysfont_map.tsv.
      evmsg_export.SYSFONT_FILES 의 번역은 이 글자 코드로 넣는다.

주의: 이 DDS 는 텍스처가 1024x1024 일 때만 맞다. 게임마다 tools/re/mem.py tex2x 필요 (영구 처리 미정).

글자 배정: 번역에 쓰인 글자 중 원본 문자표(evmsg.LATIN)에 없는 것. 많이 쓰인 순서로
  idx 126~139 (1바이트 9E~AB) -> 224~479 (2바이트 19xx) -> 736~1343 (1Bxx~1Fxx) -> 221~223 (1바이트 FD~FF, 미검증)
  480~735 (1Axx) 는 msg_layout 이 공백 처리하므로 쓰지 않는다. 둘째 바이트 00/04 인 칸도 뺀다.

사용 (openkh_venv python -I):
  python tools/build_ko.py            확인만 (무엇을 쓸지 출력)
  python tools/build_ko.py --apply    mod/kh1 에 쓴다
  --layout jp   일본어판 배치 (21줄 x 24px, 1764칸). 셀을 세로 24/32 로 줄여 넣음. 게임에서는 mem.py tex2x ... jp 필요 (28차, 29차)
"""
import collections, glob, os, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import allarea, evmsg, evmsg_export, knj_tex1024 as kt, moviesub, sysfont, tr_batch

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "kh1")
MOD = os.path.join(ROOT, "mod", "kh1")
DDS_REL = "remastered/exchange/UK_kanji.knj/UK_kanji_knj0.dds"
KNJ_REL = "exchange/UK_kanji.knj"
MAP_OUT = os.path.join(ROOT, "translation", "build", "glyph_map.tsv")
SMAP_OUT = os.path.join(ROOT, "translation", "build", "sysfont_map.tsv")   # 시스템 글꼴 글자 (40차)

def make_pool(layout):
    count = kt.LAYOUTS[layout]["count"]
    # 172~216 = 악센트 라틴 (CC~F8). 영어 원문에서 쓰이지 않음 (2026-10-29 확인) -> 맨 뒤에 재사용
    pool = (list(range(126, 140)) + list(range(224, 480)) + list(range(736, count))
            + list(range(221, 224)) + list(range(172, 217)))
    # 2바이트 둘째 바이트가 메시지 끝 코드(0x00, 0x04)와 같은 칸은 피한다 (끝을 단순 검색하는 경로가 있을 수 있음, 미확인)
    return [i for i in pool if i < 224 or (i + 0x1820) & 0xFF not in (0x00, 0x04)]


FONT = r"C:\Windows\Fonts\malgun.ttf"
FONT_PX = 75            # 4096 DDS 기준 (PS2 1px = 4px). 18차(8배, 150px)와 같은 비율
HANGUL_WIDTH = 22       # 폭 표 값 (18차와 같음)
GLYPH_CX = 50           # 셀(96 폭) 안 가로 중심
GLYPH_BOTTOM = 107      # '사' 아래 끝: 18차 글리프 위치를 4배로 환산 (셀 96x128 기준)
OUTLINE = 4             # 검정 테두리 두께 (4096 기준 px). 원본 영문 테두리 약 1 PS2px
# 53차: 게임은 이 텍스처를 밉맵 없이 약 2.6배 줄여 그린다 (1080p 상점 문구 기준, 추정). 날카로운 획이 글자마다 1~2px 로
# 들쭉날쭉해지므로 (사용자 화면), 미리 살짝 흐리게 한 뒤 진하기를 되돌린다. 값은 축소 시뮬레이션으로 고름
SOFTEN, SOFTEN_GAIN = 1.3, 1.5
# jp 배치: 텍스처 셀은 24 높이지만 화면에는 32 높이로 그려진다 (28차 화면: 글자가 세로로 약 1.33배).
# 그래서 영어 배치(24x32)로 그린 셀을 세로만 24/32 로 줄여 넣는다 -> 화면에서는 원래 비율.
KNJ_JP_SIZE = 0x40800   # jp 배치 폭 표(1764칸)를 담는 크기 = 일본어판 kanji.knj 크기
TOKEN = re.compile(r"\[[^\]]*\]|\{[^}]*\}|<[^>]*>|\\n")


OFFSET = re.compile(r"\[0B 00 ([0-9A-F]{2}) ([0-9A-F]{2})\]")


def recenter(en, ko):
    """가운데 정렬 자막의 x 오프셋을 번역 폭에 맞춘다 (36차).
    대상: <00> 로 끝나고 모든 줄이 같은 음수 [0B 00 lo hi] 로 시작 위치를 정한 메시지.
    원문 통계 (108개): 오프셋 = -(최대 줄 폭)/2 + 약 5 (중앙값 오차 3.5). msg_layout 은 자동 줄바꿈·정렬이 없다 (exe-analysis 5절).
    번역 오프셋이 원문 값 그대로일 때만 (원문 최대 폭 - 번역 최대 폭)/2 를 더한다."""
    offs = set(OFFSET.findall(en))
    if not en.endswith("<00>") or len(offs) != 1 or set(OFFSET.findall(ko)) != offs:
        return ko
    lo, hi = offs.pop()
    o = int(hi + lo, 16)
    if o < 0x8000 or len(OFFSET.findall(en)) != len(tr_batch.lines(en)):
        return ko
    ew = max(tr_batch.line_width(l) for l in tr_batch.lines(en))
    kw = max(tr_batch.line_width(l) for l in tr_batch.lines(ko))
    n = (o - 0x10000 + round((ew - kw) / 2)) & 0xFFFF
    return OFFSET.sub(f"[0B 00 {n & 0xFF:02X} {n >> 8:02X}]", ko)


def glyph_chars(text):
    return [c for c in TOKEN.sub("", text) if c not in evmsg.CHAR_CODE]


def render_cell(font, ch, baseline, cell_h):
    # 원본 글리프 구조 (30차 확인): RGB = 회색 128 x 채움 커버리지, 알파 = 윤곽(채움 + 테두리) 커버리지.
    # 테두리는 검정(RGB 0)으로 보이고 알파가 계조라 가장자리가 부드럽다.
    size = (kt.CELL_W * kt.SCALE, cell_h * kt.SCALE)
    fill, edge = Image.new("L", size, 0), Image.new("L", size, 0)
    ImageDraw.Draw(fill).text((GLYPH_CX, baseline), ch, font=font, fill=255, anchor="ms")
    ImageDraw.Draw(edge).text((GLYPH_CX, baseline), ch, font=font, fill=255, anchor="ms",
                              stroke_width=OUTLINE, stroke_fill=255)
    fill, edge = (m.filter(ImageFilter.GaussianBlur(SOFTEN)).point(lambda v: min(255, round(v * SOFTEN_GAIN)))
                  for m in (fill, edge))
    gray = fill.point(lambda v: (128 * v + 127) // 255)
    return Image.merge("RGBA", (gray, gray, gray, edge))


def main(apply, layout):
    POOL = make_pool(layout)
    cell_h = kt.LAYOUTS[layout]["cell_h"]
    print(f"배치 {layout}: {kt.LAYOUTS[layout]}")
    rows = evmsg_export.read_tsv(evmsg_export.OUT)
    ko = {k: recenter(r["en"], r["ko"]) for k, r in rows.items() if r.get("ko")}
    loc = {p: (en, recenter(en, t)) for p, (en, t) in evmsg_export.read_loc().items()}   # 위치별 번역 (49차)
    moved = sum(ko[k] != rows[k]["ko"] for k in ko)
    print(f"가운데 정렬 자막 오프셋 보정: {moved}개")

    # 1. 글자 배정. 파일 종류별로 센다: 대화창 글꼴 / 시스템 글꼴 / 공유 (42차: 대화창 [0E xx] 가 끼워 넣는
    #    아이템·어빌리티 이름은 두 글꼴에서 같은 코드여야 하므로 두 글꼴 모두 쓸 수 있는 idx 에 먼저 둔다)
    freq, sfreq, shared = collections.Counter(), collections.Counter(), collections.Counter()
    for rel, b in evmsg_export.source_files():
        msgs, refd = evmsg_export.messages(rel, b)
        cnt = sfreq if rel in evmsg_export.SYSFONT_FILES else freq
        for i in refd:
            for c in glyph_chars(evmsg_export.lookup(ko, loc, rel, i, msgs[i]) or ""):
                cnt[c] += 1
                if rel in evmsg_export.SHARED_FILES:
                    shared[c] += 1
    for t in moviesub.texts():             # 영상 자막 (대화창 글꼴, mem.py 가 게임 안에 붙인다)
        for c in glyph_chars(t):
            freq[c] += 1
    order =lambda f: sorted(f, key=lambda c: (-f[c], c))
    s_idx = sysfont.slot_indices()
    both = [i for i in s_idx if i in set(POOL)]
    if len(shared) > len(both):
        sys.exit(f"공유 글자 {len(shared)}개 > 공유 칸 {len(both)}개")
    fixed = dict(zip(order(shared), both))
    chars = order(freq)
    dchars = [c for c in chars if c not in fixed]
    dpool = [i for i in POOL if i not in set(fixed.values())]
    if len(dchars) > len(dpool):
        sys.exit(f"글자 {len(dchars)}개 > 칸 {len(dpool)}개 (공유 {len(fixed)}개 별도)")
    assign = dict(fixed)
    assign.update(zip(dchars, dpool))
    chars = list(fixed) + dchars
    for c in fixed:
        freq.setdefault(c, 0)
    gbytes = {c: evmsg.idx_to_bytes(i) for c, i in assign.items()}
    print(f"번역 {len(ko)}줄, 대화창 글자 {len(chars)}개 (공유 {len(fixed)}개 포함, 칸 {len(POOL)}개 중)")

    # 1-1. 시스템 글꼴 글자 배정 (SYSFONT_FILES 의 번역만). 공유 글자는 같은 idx
    area_tr = allarea.read_tsv()           # 장소 이름 (42차): 시스템 글꼴 레코드를 Shift-JIS 가짜 코드로 찾는다
    for c in allarea.chars(area_tr):
        sfreq[c] += 1
    schars = order(sfreq)
    s_tbl, s_hdr, s_img, s_gbytes, s_placed = sysfont.build(schars, fixed)
    print(f"시스템 글꼴: 글자 {len(schars)}개 (공유 {len(fixed)}개 포함)")

    area_codes = {c: sysfont.sjis_code(i) for c, i, _, _ in s_placed}
    area_rel = allarea.REL
    area_bytes = allarea.build(open(os.path.join(DATA, area_rel), "rb").read(), area_tr, area_codes)
    print(f"장소 이름: {len(area_tr)}개, {len(area_bytes)}B")

    # 2. 메시지
    out_files = {}
    restore = []
    for rel, b in evmsg_export.source_files():
        msgs, refd = evmsg_export.messages(rel, b)
        gb = s_gbytes if rel in evmsg_export.SYSFONT_FILES else gbytes
        new = [evmsg.encode(t, gb) if i in refd and (t := evmsg_export.lookup(ko, loc, rel, i, m)) else m
               for i, m in enumerate(msgs)]
        for r, nb in evmsg_export.rebuild(rel, b, new).items():
            ob = b if r == rel else open(os.path.join(DATA, r), "rb").read()
            mp = os.path.join(MOD, r)
            if nb != ob:
                out_files[r] = nb
                if r in evmsg_export.OFS_PAIRS and len(nb) > len(ob):
                    print(f"  경고: {r} 크기 {len(ob)} -> {len(nb)} (로더 버퍼 미확인)")
            elif os.path.exists(mp) and open(mp, "rb").read() != ob:
                restore.append(r)
    print(f"대사 파일: 생성/갱신 {len(out_files)}, 원본으로 되돌림 {len(restore)}")

    # 3. DDS
    hdr, base = kt.read_dds(os.path.join(DATA, DDS_REL))
    tex = Image.new("RGBA", (kt.SIZE, kt.SIZE), (0, 0, 0, 0))
    up = base.resize((kt.SIZE // 2, kt.SIZE // 2), Image.BICUBIC)   # 원본 페이지 0 (512 배치) 을 4배로
    cw, ch0, chl = kt.CELL_W * kt.SCALE, 32 * kt.SCALE, cell_h * kt.SCALE
    fit = (lambda im: im) if layout == "en" else (lambda im: im.resize((cw, chl), Image.LANCZOS))
    if layout == "en":
        tex.paste(up, (0, 0))
    else:
        for i in range(221):
            r, c = divmod(i, kt.COLS)
            tex.paste(fit(up.crop((c * cw, r * ch0, (c + 1) * cw, (r + 1) * ch0))), kt.cell_box(i, layout)[:2])
    font = ImageFont.truetype(FONT, FONT_PX)
    probe = Image.new("L", (96, 128), 0)
    ImageDraw.Draw(probe).text((GLYPH_CX, 100), "사", font=font, fill=255, anchor="ms")
    baseline = 100 + GLYPH_BOTTOM - probe.getbbox()[3]
    for c, i in assign.items():
        tex.paste(fit(render_cell(font, c, baseline, 32)), kt.cell_box(i, layout)[:2])

    # 4. 폭 표
    knj = bytearray(open(os.path.join(DATA, KNJ_REL), "rb").read())
    if layout == "jp":
        knj += bytes(max(0, KNJ_JP_SIZE - len(knj)))
    for c, i in assign.items():
        w = HANGUL_WIDTH if "\uac00" <= c <= "\ud7a3" else max(1, round(font.getlength(c) / kt.SCALE))
        knj[kt.WIDTH_TBL + i] = w

    if not apply:
        print("확인만 함 (--apply 로 쓰기)")
        for c in chars[:40]:
            print(f"  {c} idx {assign[c]} 코드 {gbytes[c].hex()} 빈도 {freq[c]}")
        return
    os.makedirs(os.path.dirname(MAP_OUT), exist_ok=True)
    with open(MAP_OUT, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("char\tidx\tcode\tfreq\n")
        for c in chars:
            fp.write(f"{c}\t{assign[c]}\t{gbytes[c].hex()}\t{freq[c]}\n")
    for rel in (DDS_REL, KNJ_REL, sysfont.TBL_REL, area_rel):    # 빈 mod 폴더에서도 (설치 프로그램)
        os.makedirs(os.path.dirname(os.path.join(MOD, rel)), exist_ok=True)
    kt.write_dds(os.path.join(MOD, DDS_REL), hdr, tex)
    open(os.path.join(MOD, KNJ_REL), "wb").write(knj)
    with open(SMAP_OUT, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("char\tidx\tcode\tx\ty\n")
        for c, i, x, y in s_placed:
            fp.write(f"{c}\t{i}\t{s_gbytes[c].hex()}\t{x}\t{y}\n")
    os.makedirs(os.path.dirname(os.path.join(MOD, sysfont.DDS_REL)), exist_ok=True)
    kt.write_dds(os.path.join(MOD, sysfont.DDS_REL), s_hdr, s_img)
    open(os.path.join(MOD, sysfont.TBL_REL), "wb").write(s_tbl[:sysfont.FILE_REC * 16])   # 게임이 읽는 앞 1024
    open(sysfont.FULL_OUT, "wb").write(s_tbl)                                             # 나머지는 mem.py 가 붙인다 (43차)
    open(os.path.join(MOD, area_rel), "wb").write(area_bytes)
    moviesub.write(moviesub.build(gbytes))
    for rel, nb in out_files.items():
        os.makedirs(os.path.dirname(os.path.join(MOD, rel)), exist_ok=True)
        open(os.path.join(MOD, rel), "wb").write(nb)
    for rel in restore:
        open(os.path.join(MOD, rel), "wb").write(open(os.path.join(DATA, rel), "rb").read())
    print(f"썼음: DDS, {KNJ_REL}, 대사 {len(out_files)}, 되돌림 {len(restore)}, {MAP_OUT}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main("--apply" in a, a[a.index("--layout") + 1] if "--layout" in a else "en")
