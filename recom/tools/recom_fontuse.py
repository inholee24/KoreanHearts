"""어느 텍스트가 어느 글꼴로 그려지는지 데이터로 판정 (게임 실행 없음).

원리: 일본어판(원본 CTD) 문장의 한자·가나 코드가 일본어판 글꼴 표(SY0001.BIN 안 sysfont.bin / evtfont.bin)
중 어느 쪽에 모두 들어 있는지. 각 표는 그 글꼴로 그려지는 텍스트에 나오는 글자만 담는다.
메시지마다 레이아웃 번호가 있으면 레이아웃 단위로도 판정한다.

사용: python -I recom_fontuse.py <Recom 추출 폴더>
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ctd, recom_ffmw, recom_fontgrid as fg

data = sys.argv[1]
b = open(os.path.join(data, "SYS", "0001", "SY0001.BIN"), "rb").read()
JP = {"sys": recom_ffmw.parse(b[0x3D70:0x3D70 + 0x3B70])["map"],
      "evt": recom_ffmw.parse(b[0x78E0:0x78E0 + 0x3D94])["map"]}


def has(kind, c):
    try:
        return JP[kind][fg.code_index(c)] != 0
    except (ValueError, IndexError):
        return False


res = collections.Counter()
rows = []
for dp, dns, fns in os.walk(data):
    if "remastered" in dp:
        continue
    for f in fns:
        if not f.upper().endswith(".CTD"):
            continue
        raw = open(os.path.join(dp, f), "rb").read()
        try:
            d = recom_ctd.parse(raw)
        except Exception:
            continue
        codes = set()
        for m in d["msgs"]:
            codes.update(c for c in fg.codes(m) if c >= 0x889F)   # 한자 영역만 (판별력 높음)
        if len(codes) < 5:
            continue
        s = sum(has("sys", c) for c in codes) / len(codes)
        e = sum(has("evt", c) for c in codes) / len(codes)
        verdict = "sys" if s > 0.98 and e < 0.9 else "evt" if e > 0.98 and s < 0.9 else "both" if s > 0.98 and e > 0.98 else "?"
        base = d["base"]
        sizes = collections.Counter(struct.unpack_from("<H", raw, base + 0x10 + 0x30 * k + 0x22)[0] for k in range(d["n_lay"]))
        top = os.path.relpath(dp, data).split(os.sep)[0].rstrip("0123456789")
        rows.append((os.path.relpath(os.path.join(dp, f), data), len(codes), round(s, 3), round(e, 3), verdict, dict(sizes)))
        res[(top, verdict)] += 1
for r in sorted(rows):
    print(*r)
print(sorted(res.items()))
