"""원본 EvMsg(.binl, UK/US) 에서 번역용 표 translation/kh1_evmsg.tsv 를 만든다 / 갱신한다.

열: key  file  idx  count  en  ko
  key   = 원문 바이트 sha1 앞 12자리 (같은 원문은 한 줄, 모든 파일에 같은 번역이 들어간다)
  file/idx = 처음 나온 위치 (문맥 확인용, 파일 이름순)
  count = 등장 횟수 (UK+US 모든 파일)
  en    = 원문 표기 (tools/evmsg.py show 형식: [제어] {코드} \\n 줄바꿈 <끝>)
  ko    = 번역. 비어 있으면 원문 그대로 둔다. 제어 [..] 와 끝 <..> 는 원문 것을 지킬 것

이미 표가 있으면 key 가 같은 줄의 ko 를 그대로 보존한다 (덮어쓰지 않음). 사라진 key 의 번역은
translation/kh1_evmsg.orphans.tsv 로 따로 남긴다.

사용: openkh_venv python -I tools/evmsg_export.py
"""
import glob, hashlib, os, sys

sys.path.insert(0, os.path.dirname(__file__))
import evmsg

ROOT = os.environ.get("KH1KO_ROOT") or os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data", "kh1")
OUT = os.path.join(ROOT, "translation", "kh1_evmsg.tsv")
LOC_OUT = os.path.join(ROOT, "translation", "kh1_evmsg_loc.tsv")   # 위치별 번역 (49차, read_loc)
COLS = ["key", "file", "idx", "count", "en", "ko"]


def key_of(m):
    return hashlib.sha1(m).hexdigest()[:12]


def source_files():
    fs = []
    for lang in ("UK", "US"):
        fs += glob.glob(os.path.join(DATA, "remastered", "**", f"{lang}_*.binl"), recursive=True)
    out = []
    for f in sorted(fs, key=lambda p: os.path.relpath(p, DATA).replace(os.sep, "/")):
        b = open(f, "rb").read()
        if b[:5] == b"EvMsg":
            out.append((os.path.relpath(f, DATA).replace(os.sep, "/"), b))
    # exchange 의 머리말 없는 메시지 파일 (u32 수 + 메시지). 37차
    for lang in ("UK", "US"):
        for name in EXCHANGE_PLAIN:
            rel = f"exchange/{lang}_{name}"
            b = open(os.path.join(DATA, rel), "rb").read()
            evmsg.parse_plain(b)   # 형식이 아니면 예외
            out.append((rel, b))
    # exchange 의 데이터 + u16 오프셋 표 파일. 38차
    for rel in OFS_PAIRS:
        out.append((rel, open(os.path.join(DATA, rel), "rb").read()))
    # btltbl 의 UI 문자열 목록. 42차
    for rel in list(UI_LISTS) + list(V361) + list(KMB):
        out.append((rel, open(os.path.join(DATA, rel), "rb").read()))
    return out


EXCHANGE_PLAIN = ("HZRankingMsg.bin", "PresentMessage.bin", "ShopMessage.bin", "gumi_shop_msg.bin", "hades_cup.bin",
                  "hercules_cup.bin", "item_shop_msg.bin", "pegasus_cup.bin", "phil_cup.bin")
# 데이터 -> 오프셋 표. 게임(영어)은 UK_ 를 읽는다 (SAWD/SAWE 는 US 데이터 파일이 없음).
# 구미 차고(SASAMSG, gumi_mes_data)는 HD 메뉴 글꼴로 그려져서(38차 화면) 시스템 글꼴 작업 때 넣는다.
OFS_PAIRS = {f"exchange/{lang}_{d}": f"exchange/{lang}_{o}" for lang, d, o in (
    ("UK", "SAWDMSG.BIN", "SAWDOMSG.BIN"), ("UK", "SAWEMSG.BIN", "SAWEOMSG.BIN"),
    ("UK", "wname_data.bin", "wname_offset.bin"), ("US", "wname_data.bin", "wname_offset.bin"),
    ("UK", "wsysmsg_data.bin", "wsysmsg_offset.bin"), ("US", "wsysmsg_data.bin", "wsysmsg_offset.bin"),
    ("UK", "name_mes.bin", "name_o_mes.bin"), ("US", "name_mes.bin", "name_o_mes.bin"),
    ("UK", "gumi_mes_data.bin", "gumi_mes_ofs.bin"))}
# 구미 차고 (42차): 데이터는 remastered 쪽, 표는 exchange. 시스템 글꼴 코드 길이로 읽는다 (UI_OFS).
# 로더 0x222424 는 원래 SASAMSG 크기의 버퍼에 HD 파일을 덮어쓴다 -> 원본 HD 파일 크기를 넘지 않게 한다 (버퍼 크기 미확인).
OFS_PAIRS["remastered/gumi/SASAMSG.BIN/UK_SASAMSG.BIN"] = "exchange/UK_SASAOMSG.BIN"
UI_OFS = {"remastered/gumi/SASAMSG.BIN/UK_SASAMSG.BIN"}
# 로더 고정 버퍼 (exe 0x2266c0: gumi_mes 데이터 0x1800, 표 0x400). 넘으면 rebuild 가 멈춘다. 42차
OFS_LIMIT = {"exchange/UK_gumi_mes_data.bin": 0x1800, "exchange/UK_gumi_mes_ofs.bin": 0x400,
             "remastered/gumi/SASAMSG.BIN/UK_SASAMSG.BIN": 12640, "exchange/UK_SASAOMSG.BIN": 560}
# 시스템(UI) 글꼴로 그려지는 파일: 대화창 글자 대신 tools/sysfont.py 의 글자 코드로 넣는다 (40차).
# 39차 화면: 월드맵 메뉴, 이름 입력 화면. SAWEMSG(구미 쉽 비행 대사)는 exe 로 확인:
# 0x2131f2 -> 0x506fc0/c8 -> 0x1f5110 -> 0x2d35d0/0x2d2970. wsysmsg(게이지)는 같은 계열로 추론.
SYSFONT_FILES = {f"exchange/{lang}_{n}" for lang in ("UK", "US") for n in ("wname_data.bin", "wsysmsg_data.bin", "name_mes.bin")}
SYSFONT_FILES |= {"exchange/UK_SAWDMSG.BIN", "exchange/UK_SAWEMSG.BIN"}
# 메뉴 이름·설명: remastered/btltbl.bin 의 UI 문자열 목록 (42차). 0x00 끝 문자열이 순서대로 이어지고 게임은 앞에서
# 정해진 개수만 읽는다 (exe 0x28f9d0: Word 512 -> 0x2d22f98, ItemHelp 255 -> 0x2d22d38 +0xC, AbilityHelp/Name
# 65 -> 0x2d36d48 +8/+4). 길이 제한 없음 (자산 데이터를 통째로 쓰고 포인터만 등록). 남는 뒷부분은 그대로 둔다.
# 게임은 '<언어>_' 뒤 이름이 정확히 같은 자산을 찾으므로 UK_btltbl_bin_*.bin 은 쓰이지 않는다 (추론).
UI_LISTS = {f"remastered/btltbl.bin/UK_{n}.bin": c for n, c in
            (("Word", 512), ("ItemHelp", 255), ("AbilityName", 65), ("AbilityHelp", 65))}
SYSFONT_FILES |= set(UI_LISTS)
# 대화창 [0E xx] 가 이 목록의 문자열을 대화창 글꼴로 끼워 넣는다 (exe 0x176df3: 아이템 이름 0x28f9b0, 어빌리티 이름
# 0x28f8f0). 그래서 여기 쓰인 글자는 두 글꼴에서 같은 코드를 써야 한다 (build_ko 공유 배정).
SHARED_FILES = {"remastered/btltbl.bin/UK_Word.bin", "remastered/btltbl.bin/UK_AbilityName.bin"}
# 구미 블록 이름·설명 (42차): 메뉴는 시스템 글꼴, 대화창 [0E 02] 가 이름을 끼워 넣는다 (exe 0x20d380 -> 0x2266c0 표)
SYSFONT_FILES.add("exchange/UK_gumi_mes_data.bin")
SYSFONT_FILES |= UI_OFS
SHARED_FILES.add("exchange/UK_gumi_mes_data.bin")
# 메뉴 시스템 메시지 "Message v361" (42차, evmsg.parse_v361). 게임은 고정 버퍼 0x4800B 에 복사한다 -> build 가 크기 확인.
V361 = {"remastered/menu/uk/sysmsg.bin/UK_sysmsg.binl": 0x4800,
        "remastered/menu/md_memo_sysmsg.bin/UK_md_memo_sysmsg.binl": 3808}   # 지미니 메모 메뉴 (43차, 버퍼 미확인 -> 원본 크기)
# 지미니 메모 본문 (43차): u32 수 + 시스템 글꼴 문자열 (0x00 끝). 로더 0x2fbb80 이 원래 파일을 메모리 풀 구역
# (md_dic_msg = 풀 0x33 +0x34000 등) 에 읽은 뒤 HD 파일을 덮어쓴다 -> 구역 크기 미확인이라 원본 HD 크기를 한도로.
KMB = {f"remastered/menu/{n}/UK_{n}": None for n in ("md_dic_msg.kmb", "md_syno.kmb", "md_jiminy.kmb", "md_anthem.kmb")}
SYSFONT_FILES |= set(V361) | set(KMB)
# 44차 화면: 본문 글자가 같은 코드의 대화창 글꼴 글자로 나왔다 (예: 시스템 1c0d '었' -> 대화창 1c0d '놈') -> 본문은
# 대화창 글꼴 (kanji_tex) 로 그려진다. 메뉴·제목은 시스템 글꼴이라 두 글꼴에서 같은 코드인 공유 배정으로 둔다.
SHARED_FILES |= set(KMB)


def ui(rel):
    """이 파일의 메시지를 시스템 글꼴 코드 길이(evmsg.code_len_ui)로 읽는가. 40차 SYSFONT_FILES 는 대화창 규칙 표기 그대로 둔다."""
    return rel in UI_LISTS or rel in V361 or rel in UI_OFS or rel in KMB


def messages(rel, b, root=DATA):
    """(메시지 목록, 번역 대상 번호 집합). 오프셋 표 형식은 표의 오프셋 파일을 root 에서 읽는다."""
    if rel in UI_LISTS:
        msgs = evmsg.split_ui(b, UI_LISTS[rel])[0]
        return msgs, set(range(len(msgs)))
    if rel in KMB:
        msgs = evmsg.split_ui(b[4:], int.from_bytes(b[:4], "little"))[0]
        return msgs, set(range(len(msgs)))
    if rel in OFS_PAIRS:
        segs, _, refs = evmsg.parse_ofs(b, open(os.path.join(root, OFS_PAIRS[rel]), "rb").read(), ui(rel))
        refd = set(refs.values())
        if rel in UI_OFS:   # 0x10 으로 끝난 조각은 다음 조각으로 이어진다 (구미 도움말 여러 쪽). 표에 없어도 번역 대상
            for i in sorted(refd):
                while segs[i][-1:] == b"\x10" and i + 1 < len(segs):
                    i += 1
                    refd.add(i)
        return segs, refd
    if rel in V361:
        segs, refs = evmsg.parse_v361(b)
        return segs, set(refs.values())
    msgs = evmsg.parse(b)[1]
    return msgs, set(range(len(msgs)))


def rebuild(rel, b, new):
    """번역한 메시지 목록으로 파일을 다시 만든다. 돌려줌: {상대 경로: bytes} (오프셋 표 형식은 표 파일도)."""
    if rel in OFS_PAIRS:
        ofs = open(os.path.join(DATA, OFS_PAIRS[rel]), "rb").read()
        _, tail, refs = evmsg.parse_ofs(b, ofs, ui(rel))
        nd, no = evmsg.serialize_ofs(new, tail, refs, b, ofs)
        for r, x in ((rel, nd), (OFS_PAIRS[rel], no)):
            if len(x) > OFS_LIMIT.get(r, len(x)):
                raise ValueError(f"{r} {len(x)}B > 게임 버퍼 {OFS_LIMIT[r]}B")
        return {rel: nd, OFS_PAIRS[rel]: no}
    if rel in UI_LISTS:
        tail = b[evmsg.split_ui(b, UI_LISTS[rel])[1]:]
        body = b"".join(new) + tail
        return {rel: body + bytes([0xCD]) * (len(b) - len(body))}   # 짧아지면 원래 크기로 채움
    if rel in KMB:
        n = int.from_bytes(b[:4], "little")
        tail = b[4 + evmsg.split_ui(b[4:], n)[1]:]
        body = b[:4] + b"".join(new)
        pad = tail[-1:] or bytes(1)
        if len(body) > len(b):
            raise ValueError(f"{rel} {len(body)}B > 원본 {len(b)}B (게임 버퍼 미확인)")
        return {rel: body + pad * (len(b) - len(body))}
    if rel in V361:
        nb = evmsg.serialize_v361(new, evmsg.parse_v361(b)[1], b)
        if len(nb) > V361[rel]:
            raise ValueError(f"{rel} {len(nb)}B > 게임 버퍼 {V361[rel]}B")
        return {rel: nb}
    head, _, tail = evmsg.parse(b)
    return {rel: evmsg.serialize(head, new, tail)}


def translatable(m, u=False):
    return any(k == "ch" and t[0] != 0x01 for k, t in evmsg.tokens(m, u))


def read_tsv(path):
    rows = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fp:
            head = fp.readline().rstrip("\n").split("\t")
            for line in fp:
                r = dict(zip(head, line.rstrip("\n").split("\t")))
                rows[r["key"]] = r
    return rows


def read_loc():
    """위치별 번역 (49차): 같은 원문이라도 이 위치만 다르게 번역한다. {(file, idx): (en, ko)}.
    LOC_OUT 열: file  idx  en  ko  (en 은 확인용, 원본과 다르면 빌드가 멈춘다). key 별 번역보다 우선한다."""
    loc = {}
    if os.path.exists(LOC_OUT):
        with open(LOC_OUT, encoding="utf-8") as fp:
            head = fp.readline().rstrip("\n").split("\t")
            for line in fp:
                if line.strip():
                    r = dict(zip(head, line.rstrip("\n").split("\t")))
                    loc[(r["file"], int(r["idx"]))] = (r["en"], r["ko"])
    return loc


def lookup(ko, loc, rel, i, m):
    """이 위치의 번역 (없으면 None). ko = key 별 번역, loc = read_loc() (ko 는 build_ko.recenter 를 거친 값이어도 된다)"""
    if (rel, i) in loc:
        en, t = loc[(rel, i)]
        if en != evmsg.show(m, ui=ui(rel)):
            sys.exit(f"위치별 번역 원문 불일치: {rel}#{i} {en!r} != {evmsg.show(m, ui=ui(rel))!r}")
        return t
    return ko.get(key_of(m))


def main():
    old = read_tsv(OUT)
    rows, order = {}, []
    for rel, b in source_files():
        msgs, refd = messages(rel, b)
        for i, m in enumerate(msgs):
            if i not in refd or not translatable(m, ui(rel)):
                continue
            k = key_of(m)
            if k not in rows:
                rows[k] = {"key": k, "file": rel, "idx": str(i), "count": 0, "en": evmsg.show(m, ui=ui(rel)),
                           "ko": old.get(k, {}).get("ko", "")}
                order.append(k)
            rows[k]["count"] += 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("\t".join(COLS) + "\n")
        for k in order:
            fp.write("\t".join(str(rows[k][c]) for c in COLS) + "\n")
    os.replace(tmp, OUT)
    orphans = [r for k, r in old.items() if k not in rows and r.get("ko")]
    if orphans:
        with open(OUT.replace(".tsv", ".orphans.tsv"), "a", encoding="utf-8", newline="\n") as fp:
            for r in orphans:
                fp.write("\t".join(r.get(c, "") for c in COLS) + "\n")
    done = sum(1 for k in order if rows[k]["ko"])
    print(f"{OUT}: {len(order)} 줄, 번역 {done}, 보존 실패(orphans) {len(orphans)}")


if __name__ == "__main__":
    main()
