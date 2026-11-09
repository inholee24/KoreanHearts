"""recom_build 결과 검증 (mod/recom 를 원본과 전수 대조). '문제 0' 이어야 한다.

메시지 (모든 mod UK .ctdl + 영상 자막 UK_MVS*.binl):
  - MVS: 원본 머리말·시각 + 새 문자열로 다시 만든 결과와 바이트 단위로 같은가
  - evt 만 글자(glyph_map sys_glyph -1, 자막 전용)가 CTD 메시지에 없고 sysfont 표에 연결되지 않았는가
  - 메시지 수가 같고, 머리말·레이아웃 영역 = 원본에 창 크기 보정(recom_layoutfix.fix)을 적용한 결과인가
    (보정은 레이아웃 +0x16~+0x1C 위치·크기만 바꾼다; 그 밖의 바이트가 바뀌면 불일치로 잡힌다)
  - 바뀐 메시지는 모두 번역(위치별 > key 별)이 있는 원문인가
  - 바뀐 메시지를 glyph_map 으로 해독하면 번역문과 정확히 같은가
  - 번역이 있는 원문은 모두 바뀌었는가 (번역문이 원문과 같은 경우 제외)
글꼴 (sys, evt):
  - glyph_map 의 코드 -> 칸 매핑과 폭 (> 0)
  - 영어 텍스트가 쓰는 코드의 매핑이 원본과 같고, 그 글리프 칸 그림이 원본과 화소 단위로 같은가
사용: python -I -X utf8 recom_verify.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_capacity, recom_ctd, recom_font, recom_layoutfix, recom_paths as P, recom_table as T, recom_text as X, recom_textfile as TF


def main():
    data, mod = P.DATA, P.MOD
    probs = []
    rows = T.read_tsv(os.path.join(P.TR, "build", "glyph_map.tsv"))
    rev = {int(r["code"], 16): r["char"] for r in rows}
    ko = {r["key"]: r["ko"] for r in T.read_tsv(T.FULL) if r.get("ko")}
    loc = {(r["file"], int(r["idx"])): r["ko"] for r in T.read_tsv(T.LOC_FULL) if r.get("ko")}
    nfile = nmsg = nchg = nlay = 0
    has_font = os.path.exists(os.path.join(mod, *recom_font.png_rel("sys").split("/")))
    ff_o = recom_layoutfix.ffs({k: recom_font.Font(k, data) for k in ("sys", "evt")})
    ff_m = recom_layoutfix.ffs({k: recom_font.Font(k, mod if has_font else data) for k in ("sys", "evt")})
    evt_only = {r["char"] for r in rows if int(r["sys_glyph"]) < 0}
    for rel in P.uk_text(data):
        orig = open(os.path.join(data, rel), "rb").read()
        mp = os.path.join(mod, *rel.split("/"))
        cur = open(mp, "rb").read() if os.path.exists(mp) else orig
        do, dc = TF.parse(rel, orig), TF.parse(rel, cur)
        nfile += os.path.exists(mp)
        if len(do["msgs"]) != len(dc["msgs"]):
            probs.append(f"{rel}: 메시지 수 다름"); continue
        if TF.kind(rel) == "mvs":
            # 자막: 머리말·시각은 원본 그대로, 문자열만 바뀐 파일이어야 함
            if TF.build(rel, orig, do, dc["msgs"]) != cur:
                probs.append(f"{rel}: 자막 머리말·시각이 원본과 다름"); continue
        else:
            # 머리말·레이아웃 = 원본에 창 크기 보정 규칙(recom_layoutfix)을 적용한 결과와 바이트 단위로 같아야 함
            head, lch = recom_layoutfix.fix(orig, do["msgs"], dc["msgs"], ff_o, ff_m)
            nlay += len(lch)
            if head + orig[len(head):do["tbl"]] != cur[:dc["tbl"]]:
                probs.append(f"{rel}: 머리말·레이아웃이 보정 규칙 결과와 다름"); continue
            # evt 만 글자(sysfont 에 없음)가 CTD 에 나오면 sysfont 로 그려질 때 빈칸이 된다
            for i, b in enumerate(dc["msgs"]):
                bad = evt_only & set(X.show(b, rev))
                if bad:
                    probs.append(f"{rel} #{i}: evt 만 글자 {''.join(sorted(bad))} 가 CTD 에 있음")
        for i, (a, b) in enumerate(zip(do["msgs"], dc["msgs"])):
            nmsg += 1
            want = loc.get((rel, i)) or ko.get(T.key_of(a))
            if a != b:
                nchg += 1
                if not want:
                    probs.append(f"{rel} #{i}: 번역 없는데 바뀜")
                elif X.show(b, rev) != want:
                    probs.append(f"{rel} #{i}: 해독 불일치 {X.show(b, rev)[:40]!r} != {want[:40]!r}")
            elif want and want != X.show(a):
                probs.append(f"{rel} #{i}: 번역이 있는데 안 바뀜")
    used = recom_capacity.used_codes(data)
    for kind in ("sys", "evt"):
        o = recom_font.Font(kind, data)
        m = recom_font.Font(kind, mod) if os.path.exists(os.path.join(mod, *recom_font.png_rel(kind).split("/"))) else o
        for r in rows:
            code, g = int(r["code"], 16), int(r[f"{kind}_glyph"])
            if g < 0:                         # evt 만 글자: sysfont 표는 원본 그대로 (코드 -> 0)
                if m.glyph_of(code) != 0 or o.glyph_of(code) != 0:
                    probs.append(f"{kind}: evt 만 글자 {r['char']} {r['code']} 가 sysfont 에 연결됨")
                continue
            if m.glyph_of(code) != g:
                probs.append(f"{kind}: {r['char']} {r['code']} 매핑 {m.glyph_of(code)} != {g}")
            if m.width(g) <= 0:
                probs.append(f"{kind}: {r['char']} 폭 0")
        for c in used:
            try:
                go, gm = o.glyph_of(c), m.glyph_of(c)
            except ValueError:
                continue
            if go != gm:
                probs.append(f"{kind}: 영어 코드 {c:04X} 매핑 바뀜 {go} -> {gm}")
            elif go and (o.cell_img(go).tobytes() != m.cell_img(gm).tobytes() or o.width(go) != m.width(gm)):
                probs.append(f"{kind}: 영어 글리프 {go} (코드 {c:04X}) 그림·폭이 바뀜")
    print(f"mod 파일 {nfile}, 메시지 {nmsg}, 바뀐 메시지 {nchg}, 창 크기 보정 레이아웃 {nlay}, 글자 {len(rows)}, 문제 {len(probs)}")
    for p in probs[:30]:
        print("  ", p)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
