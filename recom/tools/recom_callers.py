"""호출 사슬을 위로 거슬러 올라가며 각 함수의 참조 문자열을 보여 준다 (함수 정체 찾기).
사용: python -I recom_callers.py <주소_hex> [깊이=4]
"""
import collections, sys

IDX = r"D:\Projects\openkh\re_index_recom"
funcs = []
for l in open(IDX + r"\functions.tsv", encoding="utf-8").readlines()[1:]:
    f = l.rstrip("\n").split("\t")
    funcs.append((int(f[0], 16), int(f[1], 16)))
funcs.sort()
callers = collections.defaultdict(set)
for l in open(IDX + r"\calls.tsv", encoding="utf-8"):
    f = l.split("\t")
    try:
        callers[int(f[2].split()[0], 16)].add(int(f[0], 16))
    except ValueError:
        pass
strings = {}
for l in open(IDX + r"\strings.tsv", encoding="utf-8", errors="replace"):
    f = l.rstrip("\n").split("\t")
    if len(f) >= 4:
        strings[int(f[0], 16)] = f[3]
fstr = collections.defaultdict(list)
for l in open(IDX + r"\refs.tsv", encoding="utf-8"):
    f = l.split("\t")
    try:
        t = int(f[2], 16)
    except (ValueError, IndexError):
        continue
    if t in strings:
        fstr[int(f[0], 16)].append(strings[t])


def owner(a):
    import bisect
    i = bisect.bisect_right(funcs, (a, 1 << 62)) - 1
    return funcs[i][0] if i >= 0 and funcs[i][0] <= a < funcs[i][1] else a


def walk(a, depth, seen, ind=""):
    f = owner(a)
    s = " | ".join(dict.fromkeys(fstr.get(f, [])))[:160]
    print(f"{ind}{f:#x}  {s}")
    if depth == 0 or f in seen:
        return
    seen.add(f)
    for c in sorted(callers.get(f, ()))[:12]:
        walk(c, depth - 1, seen, ind + "  ")


walk(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 4, set())
