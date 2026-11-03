"""번역 표 줄이기/펼치기: 저장소에는 원문(영어)을 넣지 않는다.

  translation/src/*.tsv   저장소에 들어가는 표. 키와 한글만 (원문 없음)
  translation/*.tsv       도구가 쓰는 전체 표 (원문 포함). data/ 의 원본에서 다시 만든다 (저장소 제외)

  python tools/tables.py expand   src + data/ 원본 -> 전체 표
  python tools/tables.py strip    전체 표 -> src (커밋 전에)
  python tools/tables.py check    strip 후 expand 결과가 지금 전체 표와 같은지 (파일을 바꾸지 않음)

키: kh1_evmsg = 메시지 key (evmsg_export.key_of), loc = (file, idx), settingmenu = flags:id,
    allarea = 원문 이름의 md5 앞 12자리 (원문 대신).
"""
import hashlib, io, os, sys

sys.path.insert(0, os.path.dirname(__file__))
import allarea, ctd, evmsg, evmsg_export as ex

ROOT = ex.ROOT
TR = os.path.join(ROOT, "translation")
SRC = os.path.join(TR, "src")
FULL = {n: os.path.join(TR, n) for n in ("kh1_evmsg.tsv", "kh1_evmsg_loc.tsv", "allarea.tsv", "settingmenu.tsv")}


def rows(path):
    with open(path, encoding="utf-8") as fp:
        head = fp.readline().rstrip("\n").split("\t")
        return head, [dict(zip(head, l.rstrip("\n").split("\t"))) for l in fp if l.strip("\n")]


def write(path, head, rs):
    buf = io.StringIO()
    buf.write("\t".join(head) + "\n")
    for r in rs:
        buf.write("\t".join(str(r.get(c, "")) for c in head) + "\n")
    return buf.getvalue()


def akey(en):
    return hashlib.md5(en.encode("utf-8")).hexdigest()[:12]


def strip():
    out = {}
    _, rs = rows(FULL["kh1_evmsg.tsv"])
    out["kh1_evmsg.tsv"] = write(None, ["key", "ko"], [r for r in rs if r.get("ko")])
    _, rs = rows(FULL["kh1_evmsg_loc.tsv"])
    out["kh1_evmsg_loc.tsv"] = write(None, ["file", "idx", "ko"], rs)
    _, rs = rows(FULL["allarea.tsv"])
    out["allarea.tsv"] = write(None, ["key", "ko"], [{"key": akey(r["en"]), "ko": r["ko"]} for r in rs])
    _, rs = rows(FULL["settingmenu.tsv"])
    out["settingmenu.tsv"] = write(None, ["key", "ko"], rs)
    return out


def expand(src):
    """src: {이름: 줄인 표 텍스트} -> {이름: 전체 표 텍스트}"""
    def parse(t):
        lines = [l for l in t.split("\n") if l]
        head = lines[0].split("\t")
        return [dict(zip(head, l.split("\t"))) for l in lines[1:]]
    out = {}
    # kh1_evmsg: evmsg_export.main 과 같은 순서·열로 원본에서 다시 만든다
    ko = {r["key"]: r["ko"] for r in parse(src["kh1_evmsg.tsv"])}
    rs, order = {}, []
    for rel, b in ex.source_files():
        msgs, refd = ex.messages(rel, b)
        for i, m in enumerate(msgs):
            if i not in refd or not ex.translatable(m, ex.ui(rel)):
                continue
            k = ex.key_of(m)
            if k not in rs:
                rs[k] = {"key": k, "file": rel, "idx": str(i), "count": 0, "en": evmsg.show(m, ui=ex.ui(rel)), "ko": ko.get(k, "")}
                order.append(k)
            rs[k]["count"] += 1
    lost = set(ko) - set(rs)
    if lost:
        raise ValueError(f"원본에 없는 번역 키 {len(lost)}개 (게임 버전이 다를 수 있음): {sorted(lost)[:5]}")
    out["kh1_evmsg.tsv"] = write(None, ex.COLS, [rs[k] for k in order])
    # loc: 그 위치의 원문
    loc = []
    for r in parse(src["kh1_evmsg_loc.tsv"]):
        rel, i = r["file"], int(r["idx"])
        msgs, _ = ex.messages(rel, open(os.path.join(ex.DATA, rel), "rb").read())
        loc.append({"file": rel, "idx": r["idx"], "en": evmsg.show(msgs[i], ui=ex.ui(rel)), "ko": r["ko"]})
    out["kh1_evmsg_loc.tsv"] = write(None, ["file", "idx", "en", "ko"], loc)
    # allarea: 키 -> 원문 이름
    names = {}
    for ws in allarea.parse(open(os.path.join(ex.DATA, allarea.REL), "rb").read()):
        for nm in ws:
            en = allarea.en_of(nm)
            names[akey(en)] = en
    ar = []
    for r in parse(src["allarea.tsv"]):
        if r["key"] not in names:
            raise ValueError(f"allarea 원문을 찾지 못함: {r['key']}")
        ar.append({"en": names[r["key"]], "ko": r["ko"]})
    out["allarea.tsv"] = write(None, ["en", "ko"], ar)
    # settingmenu: flags:id -> 원문 (ctd.show 형식)
    d = ctd.parse(open(os.path.join(ROOT, "data", "settingmenu", "uk", "ctd", "ct00100.ctd"), "rb").read())
    sm = {f"{m['flags']:04x}:{m['id']:04x}": ctd.show(m["text"]) for m in d["msgs"]}
    out["settingmenu.tsv"] = write(None, ["key", "en", "ko"],
                                   [{"key": r["key"], "en": sm[r["key"]], "ko": r["ko"]} for r in parse(src["settingmenu.tsv"])])
    return out


def main(cmd):
    if cmd == "strip":
        os.makedirs(SRC, exist_ok=True)
        for n, t in strip().items():
            open(os.path.join(SRC, n), "w", encoding="utf-8", newline="\n").write(t)
        print("src 갱신:", SRC)
    elif cmd == "expand":
        src = {n: open(os.path.join(SRC, n), encoding="utf-8").read() for n in FULL}
        for n, t in expand(src).items():
            open(FULL[n], "w", encoding="utf-8", newline="\n").write(t)
        print("전체 표 갱신:", TR)
    elif cmd == "check":
        got = expand(strip())
        bad = 0
        for n, t in got.items():
            cur = open(FULL[n], encoding="utf-8").read()
            if cur != t:
                bad += 1
                a, b = cur.split("\n"), t.split("\n")
                diff = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y][:3]
                print(f"다름 {n}: 줄 {len(a)} vs {len(b)}", *[f"\n  {i}: {x[:90]!r}\n   -> {y[:90]!r}" for i, x, y in diff])
            else:
                print(f"같음 {n}")
        return 1 if bad else 0
    else:
        print(__doc__)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
