r"""번역 작업 도구 (KH1 tr_batch.py 방식): 번역 표(translation/recom_ctd.tsv)에서 일감을 꺼내고, 검사해 합친다.

  python recom_tr.py stats                         진행 현황 (폴더별), 한글 글자 수 / 칸 (recom_capacity)
  python recom_tr.py next <N> [경로앞부분]           번역 안 된 줄 N개 -> "key<TAB>en<TAB>file#idx" (파일 순서)
  python recom_tr.py apply <파일> [--force]          "key<TAB>ko" 줄을 검사해 표에 넣는다 (같은 key 는 덮어씀)
  python recom_tr.py show <key|문자열>              key 또는 원문 일부로 줄 찾기 (문맥 확인)

검사 (apply):
  - 구조 토큰 ([F9 59] 같은 제어 코드, %s/%d, <XX>) 의 순서가 원문과 같아야 한다 (\n 위치는 달라도 됨)
  - 글자: 글꼴에 있는 ASCII, 한글(가~힣), 표기 토큰만 ({XXXX} 2바이트는 원문에 있던 것만)
  - 줄 폭(폭 표 단위, 공백 = 칸x3/8) > max(원문 최대 줄 폭 x 1.15, 원문 + 한글 1자) 이면 경고 -> --force 없으면 넣지 않음
  - %s 바로 뒤에 받침에 따라 바뀌는 조사(은/는/이/가/을/를/와/과/으로/로)가 붙으면 경고 (kh1-lessons: 이름 삽입 뒤 조사 금지)
"""
import collections, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_font, recom_paths as P, recom_table as T, recom_text as X, recom_textfile as TF

CELL = {"sys": 20, "evt": 26}
HANGUL_U = None
JOSA = re.compile(r"%[0-9]*[sd](은|는|이|가|을|를|와|과|으로|로)(?![가-힣])")
_fonts, _hangul = {}, {}
# 영상 자막(MVS): 고정 창 416x46 (exe 0x2995A0), evtfont 크기 22 -> 줄 폭 <= MVS_PX, 줄 수 <= 2
MVS_PX, MVS_SIZE, MVS_LINES = 400, 22, 2


def font(kind="sys"):
    global HANGUL_U
    if kind not in _fonts:
        _fonts[kind] = recom_font.Font(kind)
        _hangul[kind] = max(recom_font.render(kind, c)[1] for c in "가힣뷁몸")
        if kind == "sys":
            HANGUL_U = _hangul[kind]
    return _fonts[kind]


def line_widths(s, kind="sys"):
    """줄 폭 (폭 표 단위 = 칸 크기 글자일 때 PS2 px)."""
    f = font(kind)
    cell = CELL[kind]
    out, w = [], 0.0
    for t in X.tokens(s):
        if t == "\\n":
            out.append(w); w = 0.0; continue
        if t == " ":
            w += cell * 3 / 8; continue
        if t[0] == "[" and len(t) == 7:
            w += cell if t[1:3] in ("F5", "F6") else 0; continue
        if X.is_hangul(t):
            w += _hangul[kind]; continue
        if t[0] in "{<" and len(t) > 1:
            code = int(t[1:-1], 16)
        else:
            code = ord(t)
        try:
            w += f.width(f.glyph_of(code))
        except ValueError:
            w += cell
    out.append(w)
    return out


def check(en, ko, mvs=False):
    """-> (오류 목록, 경고 목록)."""
    err, warn = [], []
    if X.structure(en) != X.structure(ko):
        err.append(f"구조 토큰 다름: {X.structure(en)} != {X.structure(ko)}")
    en_codes = {t for t in X.tokens(en) if t.startswith("{") and len(t) == 6}
    f = font()
    for t in X.tokens(ko):
        if len(t) == 1 and not X.is_hangul(t):
            if not (0x20 <= ord(t) < 0x7F):
                err.append(f"쓸 수 없는 글자 {t!r}")
            elif t != " " and f.glyph_of(ord(t)) == 0:
                err.append(f"글꼴에 없는 글자 {t!r}")
        elif t.startswith("{") and len(t) == 6 and t not in en_codes:
            err.append(f"원문에 없던 2바이트 코드 {t}")
    try:
        X.encode(ko, {c: 0x889F for c in ko if X.is_hangul(c)})
    except ValueError as e:
        err.append(str(e))
    if mvs:                                  # 자막: 고정 창 기준 (원문 대비 아님)
        lw = line_widths(ko, "evt")
        px = max(lw) * MVS_SIZE / CELL["evt"]
        if px > MVS_PX:
            warn.append(f"자막 줄 폭 {px:.0f}px > {MVS_PX}")
        if len(lw) > max(MVS_LINES, len(line_widths(en, "evt"))):
            warn.append(f"자막 줄 수 {len(lw)} > {MVS_LINES}")
        if JOSA.search(ko):
            warn.append(f"%s 뒤 조사: {JOSA.search(ko).group(0)}")
        return err, warn
    ew, kw = max(line_widths(en)), max(line_widths(ko))
    lim = max(ew * 1.15, ew + HANGUL_U)
    if kw > lim:
        warn.append(f"줄 폭 {kw:.0f} > 허용 {lim:.0f} (원문 {ew:.0f})")
    if JOSA.search(ko):
        warn.append(f"%s 뒤 조사: {JOSA.search(ko).group(0)}")
    return err, warn


def main(a):
    rows = T.read_tsv(T.FULL)
    if a[0] == "stats":
        tot, done = collections.Counter(), collections.Counter()
        chars, ctd_chars = set(), set()
        ctd_keys = {T.key_of(m) for rel, _, m in T.messages() if TF.kind(rel) == "ctd"}
        for r in rows:
            top = "MVS" if TF.kind(r["file"]) == "mvs" else r["file"].split("/")[1].rstrip("0123456789")
            tot[top] += 1
            if r["ko"]:
                done[top] += 1
                hs = {c for c in r["ko"] if X.is_hangul(c)}
                chars |= hs
                if r["key"] in ctd_keys:
                    ctd_chars |= hs
        for k in sorted(tot):
            print(f"{k:8s} {done[k]:5d} / {tot[k]}")
        import recom_capacity
        used = recom_capacity.used_codes(P.DATA)
        cap = {k: len(recom_capacity.free_cells(P.DATA, k, used)[0]) for k in ("sys", "evt")}
        print(f"전체 {sum(done.values())} / {sum(tot.values())}, 한글 {len(chars)}자 "
              f"(CTD 에 나옴 {len(ctd_chars)} / sysfont 칸 {cap['sys']}, 전체 / evtfont 칸 {cap['evt']})")
    elif a[0] == "next":
        n = int(a[1]); pre = a[2] if len(a) > 2 else ""
        k = 0
        for r in rows:
            if not r["ko"] and r["file"].startswith(pre) and k < n:
                print(f"{r['key']}\t{r['en']}\t{r['file'].split('/')[-3]}#{r['idx']}")
                k += 1
    elif a[0] == "show":
        q = a[1]
        for r in rows:
            if r["key"] == q or q in r["en"]:
                print(f"{r['key']}\t{r['count']}\t{r['file']}#{r['idx']}\t{r['en']}\t{r['ko']}")
    elif a[0] == "apply":
        force = "--force" in a
        by = {r["key"]: r for r in rows}
        new, bad = {}, 0
        for ln in open(a[1], encoding="utf-8").read().split("\n"):
            if not ln.strip() or ln.startswith("#"):
                continue
            k, ko = ln.split("\t")[:2] if "\t" in ln else ln.split(" | ", 1)   # "key | 번역" 도 받음 (번역 끝 공백 보존)
            k = k.strip()
            if k not in by:
                print("없는 key:", k); bad += 1; continue
            err, warn = check(by[k]["en"], ko, mvs=TF.kind(by[k]["file"]) == "mvs")
            for e in err:
                print(f"오류 {k}: {e}  | {ko}")
            for w in warn:
                print(f"경고 {k}: {w}  | {ko}")
            if err or (warn and not force):
                bad += 1; continue
            new[k] = ko
        for r in rows:
            if r["key"] in new:
                r["ko"] = new[r["key"]]
        T.write_tsv(T.FULL, T.HEAD, rows)
        print(f"넣음 {len(new)}, 못 넣음 {bad}")
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
