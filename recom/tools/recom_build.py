"""번역 표 -> mod/recom 한글 적용본 (원본에서 매번 새로 만든다).

  python recom_build.py            확인만 (새 글자 수, 칸, 바뀔 파일 수)
  python recom_build.py --apply    mod/recom 에 쓴다

만드는 것:
  remastered/SYS/0001/SY0001.VTM/UK_{sys,evt}font_fo240.png   한글 글리프 (두 글꼴 모두)
  remastered/SYS/0001/SY0001.BIN/UK_{sys,evt}font.binl        코드 -> 글리프 매핑, 폭
  remastered/**/UK_*.ctdl, UK_MVS*.binl                        번역이 있는 메시지를 바꾼 파일 (MVS = 영상 자막)
  translation/build/glyph_map.tsv                              글자 -> 코드 / sys 칸 / evt 칸 / 폭 (검증·시뮬레이터용)
설계 (file-formats.md "글꼴 선택"): 한글 한 글자 = 코드 하나, 두 글꼴 표에 각각 칸을 연결 -> 어느 글꼴로 그려져도 맞다.
  단 MVS 자막에만 나오는 글자는 evtfont 에만 넣는다 (자막은 evtfont 로만 그려짐, sysfont 칸 963 절약).
코드: 한자 영역(lead 0x88~0x9F, 0xE0~0xE5)에서 두 표 모두 0 이고 영어 텍스트가 안 쓰는 코드.
칸: recom_capacity.free_cells (영어 텍스트 사용 글리프·□·sysfont 아이콘 영역 제외). 모자라면 멈춘다.
"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_capacity, recom_ctd, recom_font, recom_fontgrid as fg, recom_layoutfix, recom_paths as P, recom_table as T, recom_text as X, recom_textfile as TF

GLYPH_MAP = os.path.join(P.TR, "build", "glyph_map.tsv")


def load_translations():
    ko = {r["key"]: r["ko"] for r in T.read_tsv(T.FULL) if r.get("ko")}
    loc = {(r["file"], int(r["idx"])): r for r in T.read_tsv(T.LOC_FULL) if r.get("ko")}
    return ko, loc


def check_loc(loc, data):
    for (rel, i), r in loc.items():
        m = TF.parse(rel, open(os.path.join(data, rel), "rb").read())["msgs"][i]
        if X.show(m) != r["en"]:
            raise SystemExit(f"위치별 번역의 원문이 원본과 다름: {rel} #{i}")


def hangul_freq(ko, loc, msgs):
    """한글 -> 빈도, 그리고 CTD(.ctdl) 에 나오는 한글 집합 (두 글꼴 필요). 나머지는 MVS 자막에만 = evtfont 만."""
    cnt = collections.Counter()
    weight = collections.Counter(T.key_of(m) for _, _, m in msgs)
    ctd_keys = {T.key_of(m) for rel, _, m in msgs if TF.kind(rel) == "ctd"}
    in_ctd = set()
    for k, s in ko.items():
        for ch in s:
            if X.is_hangul(ch):
                cnt[ch] += weight.get(k, 1)
                if k in ctd_keys:
                    in_ctd.add(ch)
    for (rel, _), r in loc.items():
        for ch in r["ko"]:
            if X.is_hangul(ch):
                cnt[ch] += 1
                if TF.kind(rel) == "ctd":
                    in_ctd.add(ch)
    return cnt, in_ctd


def code_pool(fonts, used):
    out = []
    for i in range(864 + (0x88 - 0x87) * 192, 6816):
        code = fg.index_code(i)
        lead, trail = code >> 8, code & 0xFF
        if not (0x88 <= lead <= 0x9F or 0xE0 <= lead <= 0xE5) or trail < 0x40:
            continue
        if code in used or any(f.glyph_of(code) for f in fonts.values()):
            continue
        out.append(code)
    return out


def main(apply):
    data, mod = P.DATA, P.MOD
    ko, loc = load_translations()
    check_loc(loc, data)
    msgs = T.messages(data)
    freq, in_ctd = hangul_freq(ko, loc, msgs)
    order = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    both = [c for c, _ in order if c in in_ctd]          # CTD 에 나옴 -> sys + evt
    evt_only = [c for c, _ in order if c not in in_ctd]  # MVS 자막에만 -> evt 만 (자막 = evtfont, 확정)
    chars = both + evt_only
    used = recom_capacity.used_codes(data)
    fonts = {k: recom_font.Font(k, data) for k in ("sys", "evt")}
    pools = {k: recom_capacity.free_cells(data, k, used)[0] for k in fonts}
    codes = code_pool(fonts, used)
    print(f"번역 {len(ko)}줄 + 위치별 {len(loc)}, 한글 {len(chars)}자 (두 글꼴 {len(both)} + evt 만 {len(evt_only)}) "
          f"/ 칸 sys {len(pools['sys'])} evt {len(pools['evt'])}, 코드 {len(codes)}")
    if len(both) > len(pools["sys"]) or len(chars) > min(len(pools["evt"]), len(codes)):
        raise SystemExit(f"칸 부족: 두 글꼴 {len(both)} / sys {len(pools['sys'])}, 전체 {len(chars)} / evt {len(pools['evt'])} -> 멈춤 (known-issues 2 참조)")
    charmap, rows = {}, []
    for n, (ch, code, ge) in enumerate(zip(chars, codes, pools["evt"])):
        gs = pools["sys"][n] if n < len(both) else None
        charmap[ch] = code
        rows.append((ch, code, gs, ge))

    # 글꼴 고치기 (메모리; 저장은 --apply 때). 레이아웃 보정이 번역 글리프 폭을 쓰므로 메시지보다 먼저
    ff_orig = recom_layoutfix.ffs({k: recom_font.Font(k, data) for k in fonts})
    for k, f in fonts.items():
        if k == "evt":                       # 아래 두 페이지(□ 잔재, 표가 안 가리킴)는 비운다. 지킬 글리프 칸은 남김
            keep = recom_capacity.free_cells(data, k, used)[1]
            per = 19 * 19
            for g in range(2 * per, min(4 * per, f.ff["a"] - 0x10)):
                if g not in keep:
                    f.clear(g)
        for ch, code, gs, ge in rows:
            g = gs if k == "sys" else ge
            if g is None:                    # evt 만 글자: sysfont 표는 원본 그대로 (코드 -> 0)
                continue
            f.put(g, ch)
            f.set_map(code, g)
    ff_new = recom_layoutfix.ffs(fonts)

    # 메시지 다시 만들기 + 레이아웃(창) 크기 보정
    lay_files = lay_n = 0
    by_file = collections.defaultdict(list)
    for rel, i, m in msgs:
        by_file[rel].append((i, m))
    out_files, changed, grown = {}, 0, 0
    for rel, items in by_file.items():
        raw = open(os.path.join(data, rel), "rb").read()
        d = TF.parse(rel, raw)
        new = list(d["msgs"])
        hit = False
        for i, m in items:
            r = loc.get((rel, i))
            s = r["ko"] if r else ko.get(T.key_of(m))
            if not s:
                continue
            new[i] = X.encode(s, charmap)
            hit = hit or new[i] != m
            changed += new[i] != m
        if hit and TF.kind(rel) == "mvs":    # 자막: 창 크기 고정(416x46, 0x2995A0) - 레이아웃 보정 없음
            nb = TF.build(rel, raw, d, new)
            out_files[rel] = nb
            grown += len(nb) > len(raw)
        elif hit:
            head, lch = recom_layoutfix.fix(raw, d["msgs"], new, ff_orig, ff_new)
            nb = recom_ctd.build(head + raw[len(head):], d, new)
            out_files[rel] = nb
            grown += len(nb) > len(raw)
            lay_files += bool(lch)
            lay_n += len(lch)
    print(f"바뀐 메시지 {changed}, 파일 {len(out_files)} (원본보다 커진 파일 {grown}), 창 크기 보정 레이아웃 {lay_n} (파일 {lay_files})")
    if not apply:
        return
    for f in fonts.values():
        f.save(mod)
    # 메시지 파일: 쓰기 + 이번에 안 바뀐 예전 결과 지우기
    for rel, nb in out_files.items():
        p = os.path.join(mod, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(nb)
    removed = 0
    for dp, dns, fns in os.walk(os.path.join(mod, "remastered")):
        for fn in fns:
            if P.is_text_file(fn):
                rel = os.path.relpath(os.path.join(dp, fn), mod).replace(os.sep, "/")
                if rel not in out_files:
                    os.remove(os.path.join(dp, fn)); removed += 1
    os.makedirs(os.path.dirname(GLYPH_MAP), exist_ok=True)
    with open(GLYPH_MAP, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("char\tcode\tsys_glyph\tevt_glyph\tsys_w\tevt_w\n")
        for ch, code, gs, ge in rows:                     # sys_glyph -1 = evt 만 글자 (MVS 자막 전용)
            sw = fonts["sys"].width(gs) if gs is not None else 0
            fp.write(f"{ch}\t{code:04X}\t{-1 if gs is None else gs}\t{ge}\t{sw}\t{fonts['evt'].width(ge)}\n")
    print(f"썼음: 글꼴 2종, 메시지 파일 {len(out_files)}, 지운 예전 파일 {removed}, {GLYPH_MAP}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
