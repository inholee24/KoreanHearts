"""build_ko.py 결과 검증: mod/kh1 의 UK/US .binl 을 원본과 비교한다.

- 메시지 수가 원본과 같은가
- 바뀐 메시지는 모두 번역 표에 ko 가 있는 원문인가
- 바뀐 메시지를 glyph_map 으로 해독하면 ko 와 정확히 같은가
- ko 가 있는 원문은 모두 바뀌었는가

사용: openkh_venv python -I -X utf8 tools/verify_build.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import evmsg, evmsg_export as ex

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOD = os.path.join(ROOT, "mod", "kh1")


def main():
    from build_ko import recenter   # build_ko 와 같은 자막 오프셋 보정을 거친 값과 비교
    ko = {k: recenter(r["en"], r["ko"]) for k, r in ex.read_tsv(ex.OUT).items() if r.get("ko")}
    loc = {p: (en, recenter(en, t)) for p, (en, t) in ex.read_loc().items()}   # 위치별 번역 (49차)
    gm = {}
    with open(os.path.join(ROOT, "translation", "build", "glyph_map.tsv"), encoding="utf-8") as fp:
        next(fp)
        for line in fp:
            c, _, code, _ = line.rstrip("\n").split("\t")
            gm[bytes.fromhex(code)] = c
    sm = {}   # 시스템 글꼴 (40차): 코드 -> 글자. 표의 유니코드(+8)와 같은지도 본다
    main = open(os.path.join(MOD, "exchange", "US_font_data_tbl.bin"), "rb").read()
    tbl = open(os.path.join(ROOT, "translation", "build", "sysfont_tbl_full.bin"), "rb").read()   # 43차: mem.py 가 올리는 전체 표
    files = msgs = changed = bad = 0
    if tbl[:len(main)] != main:
        print("게임 표 파일이 전체 표의 앞부분과 다름"); bad += 1
    with open(os.path.join(ROOT, "translation", "build", "sysfont_map.tsv"), encoding="utf-8") as fp:
        next(fp)
        for line in fp:
            c, idx, code, _, _ = line.rstrip("\n").split("\t")
            sm[bytes.fromhex(code)] = c
            if chr(int.from_bytes(tbl[int(idx) * 16 + 8:int(idx) * 16 + 10], "little")) != c:
                print(f"시스템 글꼴 표 유니코드 불일치: {c} idx {idx}"); bad += 1
    if len(main) > 0x4000:
        print(f"시스템 글꼴 표가 버퍼(0x4000)보다 큼: {len(main)}"); bad += 1
    # 장소 이름 (42차): 게임처럼 2바이트씩 표 레코드 +0..1 을 찾아 +8 유니코드로 해독 (mem.py tex2x 가 찾는 수를 1024 로)
    import allarea
    words = {tbl[i * 16:i * 16 + 2]: chr(int.from_bytes(tbl[i * 16 + 8:i * 16 + 10], "little")) for i in range(len(tbl) // 16)}
    words[b"\x81\x40"] = " "
    area_tr = allarea.read_tsv()
    orig = allarea.parse(open(os.path.join(ex.DATA, allarea.REL), "rb").read())
    mod = allarea.parse(open(os.path.join(MOD, allarea.REL), "rb").read())
    for ws_o, ws_m in zip(orig, mod):
        for o, m in zip(ws_o, ws_m):
            en = allarea.en_of(o)
            if en not in area_tr:
                continue
            got = "".join(words.get(m[i:i + 2], "?") for i in range(0, len(m), 2))
            got = allarea.to_half(got)
            if got != area_tr[en]:
                print(f"장소 이름 해독 불일치: {en} -> {got} (기대 {area_tr[en]})"); bad += 1
    # 공유 글자 (42차): 대화창이 끼워 넣는 아이템·어빌리티 이름의 글자는 두 글꼴에서 코드가 같아야 한다
    gcode = {c: k for k, c in gm.items()}
    scode = {c: k for k, c in sm.items()}
    for rel, b in ex.source_files():
        if rel in ex.SHARED_FILES:
            o, refd = ex.messages(rel, b)
            for i in refd:
                for c in set(ex.lookup(ko, loc, rel, i, o[i]) or ""):
                    if c in scode and gcode.get(c) != scode[c]:
                        print(f"공유 글자 코드 다름: {c} {rel}#{i}"); bad += 1
    for rel, b in ex.source_files():
        mp = os.path.join(MOD, rel)
        o, refd = ex.messages(rel, b)
        g = sm if rel in ex.SYSFONT_FILES else gm
        if not os.path.exists(mp):
            if any(ex.lookup(ko, loc, rel, i, m) for i, m in enumerate(o) if i in refd):
                print(f"번역이 있는데 mod 파일 없음: {rel}"); bad += 1
            continue
        files += 1
        # 오프셋 표 형식은 mod 의 표로 다시 잘라, 표가 같은 조각을 가리키는지도 함께 본다
        oroot = MOD if rel in ex.OFS_PAIRS and os.path.exists(os.path.join(MOD, ex.OFS_PAIRS[rel])) else ex.DATA
        n, nrefd = ex.messages(rel, open(mp, "rb").read(), oroot)
        if len(o) != len(n) or refd != nrefd:
            print(f"메시지 수/오프셋 다름: {rel} {len(o)} -> {len(n)}"); bad += 1
            continue
        if rel in ex.OFS_PAIRS:
            _, _, r0 = evmsg.parse_ofs(b, open(os.path.join(ex.DATA, ex.OFS_PAIRS[rel]), "rb").read(), ex.ui(rel))
            _, _, r1 = evmsg.parse_ofs(open(mp, "rb").read(), open(os.path.join(oroot, ex.OFS_PAIRS[rel]), "rb").read(), ex.ui(rel))
            if r0 != r1:
                print(f"오프셋 표 칸 대응 다름: {rel}"); bad += 1
                continue
        for i, (x, y) in enumerate(zip(o, n)):
            msgs += 1
            if i not in refd:
                if x != y:
                    print(f"표가 안 가리키는 조각이 바뀜: {rel}#{i}"); bad += 1
                continue
            t = ex.lookup(ko, loc, rel, i, x)
            if x == y:
                if t:
                    print(f"번역 미적용: {rel}#{i}"); bad += 1
                continue
            changed += 1
            if not t:
                print(f"번역 없는데 바뀜: {rel}#{i}"); bad += 1
            elif evmsg.show(y, g, ex.ui(rel)) != t:
                print(f"해독 불일치: {rel}#{i}\n  {evmsg.show(y, g, ex.ui(rel))}\n  {t}"); bad += 1
    print(f"mod 파일 {files}, 메시지 {msgs}, 바뀐 메시지 {changed}, 문제 {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
