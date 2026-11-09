"""전수 왕복 확인: 모든 UK .ctdl + 영상 자막 MVS 에 대해 (1) 표기 show -> encode 가 원래 바이트와 같은가 (2) recom_ctd.build / recom_mvs.build 로 다시 쓴 파일이 원본과 바이트 같은가.
사용: python -I recom_roundtrip.py [<Recom 추출 폴더>]
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ctd, recom_text, recom_paths, recom_textfile as TF

data = sys.argv[1] if len(sys.argv) > 1 else recom_paths.DATA
nf = nm = bad_text = bad_file = 0
diffs = []
for rel in recom_paths.uk_text(data):
    b = open(os.path.join(data, rel), "rb").read()
    d = TF.parse(rel, b)
    nf += 1
    for m in d["msgs"]:
        nm += 1
        if recom_text.encode(recom_text.show(m)) != m:
            bad_text += 1
    nb = TF.build(rel, b, d, d["msgs"])
    if nb != b:
        bad_file += 1
        if len(diffs) < 5:
            k = next((i for i in range(min(len(b), len(nb))) if b[i] != nb[i]), min(len(b), len(nb)))
            diffs.append((rel, len(b), len(nb), hex(k), b[k:k + 8].hex(), nb[k:k + 8].hex()))
print(f"파일 {nf}, 메시지 {nm}, 표기 왕복 불일치 {bad_text}, 파일 재작성 불일치 {bad_file}")
for x in diffs:
    print(" ", x)
