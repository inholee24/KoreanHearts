"""CTD 레이아웃 항목(0x30 B) 필드 분포를 폴더 종류(FORM/WORLD/...)별로 비교 (글꼴 선택 필드 찾기용).
사용: python -I recom_layouts.py <Recom 추출 폴더>
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ctd

root = os.path.join(sys.argv[1], "remastered")
byfield = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
n = collections.Counter()
for dp, dns, fns in os.walk(root):
    for f in fns:
        if not (f.startswith("UK_") and f.endswith(".ctdl")):
            continue
        kind = os.path.relpath(dp, root).split(os.sep)[0].rstrip("0123456789")
        b = open(os.path.join(dp, f), "rb").read()
        d = recom_ctd.parse(b)
        for k in range(d["n_lay"]):
            e = b[0x10 + 0x30 * k: 0x40 + 0x30 * k]
            n[kind] += 1
            for off in range(0, 0x30, 2):
                byfield[off][kind][struct.unpack_from("<H", e, off)[0]] += 1
print("레이아웃 수", dict(n))
for off in range(0, 0x30, 2):
    row = {k: c.most_common(4) for k, c in byfield[off].items()}
    print(f"+{off:02X}", {k: [(hex(v), m) for v, m in vs] for k, vs in row.items()})
