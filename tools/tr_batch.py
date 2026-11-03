r"""번역 작업 도구: 번역 표(translation/kh1_evmsg.tsv)에서 일감을 꺼내고, 번역을 검사해 합친다.

사용 (openkh_venv python -I -X utf8):
  python tools/tr_batch.py stats                       진행 현황 (월드별), 새 글자 수 / 칸 873
  python tools/tr_batch.py next <N> [월드접두어]        번역 안 된 줄 N개 (파일 순서) 를 "key<TAB>en" 으로 출력
  python tools/tr_batch.py apply <파일> [--force]       "key<TAB>ko" 줄들을 검사 후 번역 표에 넣는다
  python tools/tr_batch.py width                       원문 줄 폭 분포 (검사 기준 확인용)

검사 (apply):
  - 제어 [..], 아이콘 {..}, 끝 <..> 의 순서가 원문과 같아야 한다 (\n 줄바꿈 위치는 달라도 됨)
  - 한 줄 폭이 원문 최대 줄 폭 x 1.15 와 LIMIT 중 큰 값을 넘으면 경고 (--force 없으면 넣지 않음)
  - 문자표에 없는 글자는 한글 음절(가~힣)만 허용
쓰레기 줄 (일본어판 잔여 등, junk()) 은 next 에서 건너뛴다.
"""
import collections, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
import evmsg, evmsg_export as ex

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KNJ_W = open(os.path.join(ROOT, "data", "kh1", "exchange", "UK_kanji.knj"), "rb").read()[0x40080:0x40080 + 1344]
TOKEN = re.compile(r"\[[^\]]*\]|\{[^}]*\}|<[^>]*>")
HANGUL_W = 22
SPACE_W = 8          # msg_layout 의 공백 폭 (0x4DE838, 영어 배치 = 8)
LIMIT = 440          # 번역 줄 폭 기본 허용치: 원문 줄 폭 p99 425 (width 명령, 2026-10-29). 한글 약 19자
POOL_SIZE = 1335     # 표시용. jp 배치 칸 수 (build_ko --layout jp, 30차 확정). 실제 상한 검사는 build_ko


def line_width(line):
    w = 0
    for tok in re.split(r"(\[[^\]]*\]|\{[^}]*\}|<[^>]*>)", line):
        if not tok or tok[0] in "[<":
            continue
        if tok[0] == "{":
            w += HANGUL_W
            continue
        for c in tok:
            if c == " ":
                w += SPACE_W
            elif c in evmsg.CHAR_CODE:
                w += KNJ_W[evmsg.CHAR_CODE[c] - 0x20]
            else:
                w += HANGUL_W
    return w


def lines(text):
    return text.split("\\n")


def junk(en):
    txt = re.sub(r"\[[^\]]*\]|<[^>]*>|\\n", "", en)
    # 영어 원문은 2바이트 글자({XXXX})를 쓰지 않는다 -> 있으면 일본어판 잔여
    if txt.count("{81}") >= 3 or re.search(r"\{[0-9A-F]{4}\}", txt) or len(re.findall(r"[A-Za-z]", txt)) < 0.3 * max(1, len(txt)):
        return True
    # 일본어판 잔여 (예: "h{1DF3}{1DF3}Cf", "oo", "d d"): 3글자 이상 단어도, 문장부호도 없음
    return (not re.search(r"[A-Za-z]{3,}", txt) and not re.search(r"[!?.…,\-–]", txt)
            and not re.search(r"(?:[A-Z] ){2,}[A-Z]", txt))


def load():
    with open(ex.OUT, encoding="utf-8") as fp:
        head = fp.readline().rstrip("\n").split("\t")
        rows = [dict(zip(head, l.rstrip("\n").split("\t"))) for l in fp if l.strip()]
    return head, rows


def save(head, rows):
    tmp = ex.OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("\t".join(head) + "\n")
        for r in rows:
            fp.write("\t".join(r.get(c, "") for c in head) + "\n")
    os.replace(tmp, ex.OUT)


def new_chars(rows):
    s = set()
    for r in rows:
        if r.get("ko"):
            s.update(c for c in TOKEN.sub("", r["ko"]).replace("\\n", "") if c not in evmsg.CHAR_CODE)
    return s


INDENT = re.compile(r"\\n(\[0B [0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2}\])")


def check(en, ko):
    errs = []
    # 줄머리 들여쓰기([0B ..] 가 \n 바로 뒤) 는 줄 수에 따라 늘고 줄 수 있다. 원문에 있던 값만 허용
    en_ind = set(INDENT.findall(en))
    ko_ind = INDENT.findall(ko)
    if ko_ind and not set(ko_ind) <= en_ind:
        errs.append(f"줄머리 들여쓰기가 원문에 없는 값: {sorted(set(ko_ind) - en_ind)}")
    if en_ind and en.count("\\n") == len(INDENT.findall(en)) and ko.count("\\n") != len(ko_ind):
        errs.append("원문처럼 줄바꿈마다 줄머리 들여쓰기를 붙여야 함")
    en_t, ko_t = TOKEN.findall(INDENT.sub("", en)), TOKEN.findall(INDENT.sub("", ko))
    if en_t != ko_t:
        errs.append(f"제어/아이콘 순서 다름: 원문 {en_t} / 번역 {ko_t}")
    bad = [c for c in TOKEN.sub("", ko).replace("\\n", "") if c not in evmsg.CHAR_CODE and not "가" <= c <= "힣"]
    if bad:
        errs.append(f"쓸 수 없는 글자 {''.join(sorted(set(bad)))}")
    lim = max(LIMIT, max(line_width(l) for l in lines(en)) * 1.15)
    for l in lines(ko):
        if line_width(l) > lim:
            errs.append(f"줄 폭 {line_width(l)} > {lim:.0f}: {l}")
    return errs


def main(a):
    if not a:
        print(__doc__); return 2
    head, rows = load()
    if a[0] == "stats":
        tot, done = collections.Counter(), collections.Counter()
        for r in rows:
            if junk(r["en"]):
                continue
            w = r["file"].split("/")[1].split(".")[0]
            tot[w] += 1
            done[w] += bool(r["ko"])
        for w in sorted(tot):
            print(f"{w:6} {done[w]:4}/{tot[w]:4}")
        print(f"합계 {sum(done.values())}/{sum(tot.values())}, 새 글자 {len(new_chars(rows))}/{POOL_SIZE}")
    elif a[0] == "next":
        n = int(a[1])
        pre = a[2] if len(a) > 2 else ""
        for r in rows:
            if n <= 0:
                break
            if r["ko"] or junk(r["en"]) or not r["file"].split("/")[1].startswith(pre):
                continue
            print(f"{r['key']}\t{r['en']}")
            n -= 1
    elif a[0] == "apply":
        force = "--force" in a
        by_key = {r["key"]: r for r in rows}
        ok = bad = 0
        for ln in open(a[1], encoding="utf-8").read().splitlines():
            if not ln.strip() or ln.startswith("#"):
                continue
            k, ko = ln.split("\t", 1)
            r = by_key.get(k)
            if r is None:
                print(f"없는 key {k}"); bad += 1; continue
            errs = check(r["en"], ko)
            if errs and not (force and all(e.startswith("줄 폭") for e in errs)):
                print(f"[{k}] {r['en']}\n    -> {ko}\n    " + "\n    ".join(errs)); bad += 1; continue
            r["ko"] = ko
            ok += 1
        save(head, rows)
        print(f"넣음 {ok}, 거부 {bad}, 새 글자 {len(new_chars(rows))}/{POOL_SIZE}")
    elif a[0] == "reuse":
        # 글은 같고 제어 코드 값만 다른 원문 -> 기존 번역의 제어 코드를 바꿔 재사용
        norm = lambda s: TOKEN.sub("§", s)
        src = {}
        for r in rows:
            if r["ko"]:
                src.setdefault(norm(r["en"]), r)
        n = skip = 0
        for r in rows:
            if r["ko"] or junk(r["en"]):
                continue
            s = src.get(norm(r["en"]))
            if not s:
                continue
            m = {}
            for x, y in zip(TOKEN.findall(s["en"]), TOKEN.findall(r["en"])):
                if m.setdefault(x, y) != y:
                    m = None
                    break
            if m is None:
                skip += 1
                continue
            ko = TOKEN.sub(lambda t: m.get(t.group(0), t.group(0)), s["ko"])
            if check(r["en"], ko):
                skip += 1
                continue
            r["ko"] = ko
            n += 1
        save(head, rows)
        print(f"재사용 {n}, 모호/검사 실패로 건너뜀 {skip}, 새 글자 {len(new_chars(rows))}/{POOL_SIZE}")
    elif a[0] == "width":
        ws = sorted(line_width(l) for r in rows if not junk(r["en"]) for l in lines(r["en"]))
        n = len(ws)
        print(f"원문 줄 {n}: p50 {ws[n // 2]} p90 {ws[n * 9 // 10]} p99 {ws[n * 99 // 100]} max {ws[-1]}")
        for s in ("사고 싶어요.", "아무것도 아니에요.", "무엇을 도와드릴까요?"):
            print(s, line_width(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
