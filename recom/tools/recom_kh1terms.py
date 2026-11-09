"""KH1 번역 표에서 원문이 정확히 같은 (또는 단어로 포함된) 줄의 번역을 찾는다 (용어 일관성).
사용: python -I -X utf8 recom_kh1terms.py "<영문>" ["<영문>" ...]
KH1 표: D:/Projects/kh1-korean/translation/kh1_evmsg.tsv (원문 포함 전체 표, 로컬)
"""
import re, sys

KH1 = r"D:\Projects\kh1-korean\translation\kh1_evmsg.tsv"
rows = []
for ln in open(KH1, encoding="utf-8").read().split("\n")[1:]:
    f = ln.split("\t")
    if len(f) >= 6 and f[5]:
        en = re.sub(r"\[[^\]]*\]|<[^>]*>|\{[^}]*\}", "", f[4]).replace("\\n", " ").strip()
        ko = re.sub(r"\[[^\]]*\]|<[^>]*>|\{[^}]*\}", "", f[5]).replace("\\n", " ").strip()
        rows.append((en, ko))
for q in sys.argv[1:]:
    exact = [ko for en, ko in rows if en == q]
    print(f"{q} => {sorted(set(exact))[:4] if exact else '-'}")
