"""Re:COM 번역 표 (KH1 evmsg_export + tables.py 방식).

전체 표 translation/recom_ctd.tsv (원문 포함, 저장소 제외):  key  file  idx  count  en  ko
  key   = 원문 바이트 sha1 앞 12자리 (같은 원문은 한 줄, 모든 파일에 같은 번역)
  file/idx = 처음 나온 위치 (문맥 확인용, 경로순)
  count = 등장 횟수 (UK .ctdl + 영상 자막 UK_MVS*.binl 전부: 원본·US 사본 포함)
  en/ko = recom_text 표기
저장소 표 translation/src/recom_ctd.tsv: key  ko   (원문 없음)
위치별 번역 translation/src/recom_ctd_loc.tsv: file  idx  ko   (key 별보다 우선. 원문은 expand 가 채움)

  python recom_table.py expand   원본 + src -> 전체 표 (ko 는 src 에서. 이미 있는 전체 표의 ko 도 key 로 보존)
  python recom_table.py strip    전체 표 -> src
  python recom_table.py check    strip 결과로 expand 한 표가 지금 전체 표와 같은지 (파일 안 바꿈)
번역 대상: 글자(영문자)가 있는 메시지. 기호·숫자만 있는 것은 넣지 않는다.
"""
import collections, hashlib, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ctd, recom_text, recom_textfile as TF, recom_paths as P

FULL = os.path.join(P.TR, "recom_ctd.tsv")
SRC = os.path.join(P.TR, "src", "recom_ctd.tsv")
LOC_SRC = os.path.join(P.TR, "src", "recom_ctd_loc.tsv")
LOC_FULL = os.path.join(P.TR, "recom_ctd_loc.tsv")
HEAD = ["key", "file", "idx", "count", "en", "ko"]


def key_of(m):
    return hashlib.sha1(m).hexdigest()[:12]


def translatable(m):
    return re.search(rb"[A-Za-z]{2}", m) is not None


def messages(data=None):
    """[(rel, idx, bytes)] 모든 UK 텍스트 파일(.ctdl + MVS) 메시지."""
    data = data or P.DATA
    out = []
    for rel in P.uk_text(data):
        d = TF.parse(rel, open(os.path.join(data, rel), "rb").read())
        out += [(rel, i, m) for i, m in enumerate(d["msgs"])]
    return out


def read_tsv(path):
    if not os.path.exists(path):
        return []
    lines = open(path, encoding="utf-8").read().split("\n")
    head = lines[0].split("\t")
    return [dict(zip(head, l.split("\t"))) for l in lines[1:] if l]


def write_tsv(path, head, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("\t".join(head) + "\n")
        for r in rows:
            fp.write("\t".join(str(r.get(h, "")) for h in head) + "\n")


def expand_rows(src_ko, data=None):
    first, count = {}, collections.Counter()
    for rel, i, m in messages(data):
        if not translatable(m):
            continue
        k = key_of(m)
        count[k] += 1
        first.setdefault(k, (rel, i, m))
    rows = []
    for k, (rel, i, m) in sorted(first.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        rows.append(dict(key=k, file=rel, idx=i, count=count[k], en=recom_text.show(m), ko=src_ko.get(k, "")))
    return rows


def expand_loc(data=None):
    loc = read_tsv(LOC_SRC)
    if not loc:
        return []
    data = data or P.DATA
    out = []
    for r in loc:
        d = TF.parse(r["file"], open(os.path.join(data, r["file"]), "rb").read())
        out.append(dict(file=r["file"], idx=r["idx"], en=recom_text.show(d["msgs"][int(r["idx"])]), ko=r["ko"]))
    return out


def main(cmd):
    if cmd == "expand":
        ko = {r["key"]: r["ko"] for r in read_tsv(SRC)}
        for r in read_tsv(FULL):                        # 전체 표에만 있는 번역도 보존 (strip 전 작업분)
            if r.get("ko") and not ko.get(r["key"]):
                ko[r["key"]] = r["ko"]
        rows = expand_rows(ko)
        orphans = [k for k in ko if ko[k] and k not in {r["key"] for r in rows}]
        write_tsv(FULL, HEAD, rows)
        if orphans:
            write_tsv(os.path.join(P.TR, "recom_ctd.orphans.tsv"), ["key", "ko"], [dict(key=k, ko=ko[k]) for k in orphans])
        loc = expand_loc()
        if loc:
            write_tsv(LOC_FULL, ["file", "idx", "en", "ko"], loc)
        print(f"전체 표 {len(rows)}줄 (번역 {sum(1 for r in rows if r['ko'])}), 위치별 {len(loc)}, 고아 번역 {len(orphans)} -> {FULL}")
    elif cmd == "strip":
        rows = read_tsv(FULL)
        write_tsv(SRC, ["key", "ko"], [dict(key=r["key"], ko=r["ko"]) for r in rows if r["ko"]])
        loc = read_tsv(LOC_FULL)
        if loc:
            write_tsv(LOC_SRC, ["file", "idx", "ko"], loc)
        print(f"src {sum(1 for r in rows if r['ko'])}줄 -> {SRC}")
    elif cmd == "check":
        ko = {r["key"]: r["ko"] for r in read_tsv(FULL) if r["ko"]}
        rows = expand_rows(ko)
        cur = read_tsv(FULL)
        same = [dict((h, str(r[h])) for h in HEAD) for r in rows] == [dict((h, r.get(h, "")) for h in HEAD) for r in cur]
        print("check:", "같음" if same else "다름")
        return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) or 0)
