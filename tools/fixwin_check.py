"""고정 크기 말풍선 검사 (54차): UK_*.evdl 에서 op4(tpl, w, h) 직후 op1(tpl, msg) 로 띄우는 메시지는 창 크기가 내용과 무관하다.
원문 폭 통계로 용량 = 약 31 x w 단위 (추정). 번역 최대 줄 폭 > max(원문 폭, 31w) 인 것을 n 개로 출력 (0 이어야 함).
사용: openkh_venv python -I -X utf8 tools/fixwin_check.py [덤프.json]"""
import sys, os, re, glob, struct
sys.path.insert(0, 'tools')
import evmsg, evmsg_export as ex, tr_batch as t

ko = {k: r["ko"] for k, r in ex.read_tsv(ex.OUT).items() if r.get("ko")}
OP4 = re.compile(rb"(.)\x00\x00\x09(.)\x00\x00\x09(.)\x00\x00\x09\x04\x00\x00\x18", re.S)
OP1 = re.compile(rb"(.)\x00\x00\x09(..)\x00\x09\x01\x00\x00\x18", re.S)
fixed = {}   # (dir, msg) -> set((w,h))
for ev in glob.glob(os.path.join(ex.DATA, 'remastered', '*.ard', 'UK_*.evdl')):
    b = open(ev, 'rb').read()
    d = os.path.basename(os.path.dirname(ev))
    for m in OP4.finditer(b):
        tpl, w, h = m.group(1)[0], m.group(2)[0], m.group(3)[0]
        seg = b[m.end():m.end() + 48]
        for n in OP1.finditer(seg):
            if n.group(1)[0] == tpl:
                fixed.setdefault((d, int.from_bytes(n.group(2), 'little')), set()).add((w, h))
                break
print('fixed-window messages', len(fixed))
src = dict(ex.source_files())
out = []
for (d, msg), wh in sorted(fixed.items()):
    for rel in src:
        if not rel.startswith(f'remastered/{d}/UK_') or not rel.endswith('.binl'):
            continue
        o, refd = ex.messages(rel, src[rel])
        if msg >= len(o):
            continue
        en = evmsg.show(o[msg], ui=ex.ui(rel)); k = ex.key_of(o[msg]); tr = ko.get(k)
        if not tr:
            continue
        ew = max(t.line_width(l) for l in t.lines(en)); kw = max(t.line_width(l) for l in t.lines(tr))
        out.append((kw - ew, d, msg, sorted(wh), ew, kw, len(t.lines(en)), len(t.lines(tr)), k, tr))
print('with ko', len(out), 'ko wider', sum(o[0] > 0 for o in out), 'more lines', sum(o[7] > o[6] for o in out))
for o in sorted(out, reverse=True):
    if o[0] > 0 or o[7] > o[6]:
        print(o[:9], o[9][:80])
# w -> en max width 분포 (용량 추정)
import collections
cap = collections.defaultdict(list)
for o in out:
    for w, h in o[3]:
        cap[w].append(o[4])
for w in sorted(cap):
    print('w', w, 'n', len(cap[w]), 'en max', max(cap[w]))
print('---- flagged (cap = 31*w, en consistent)')
seen = {}
for o in out:
    d_, d, msg, wh, ew, kw, el, kl, k, tr = o
    for w, h in wh:
        cap = 31 * w
        if ew <= cap + 15 and kw > max(ew, cap):
            seen.setdefault(k, (kw - max(ew, cap), d, msg, w, h, ew, kw, tr))
for k, v in sorted(seen.items(), key=lambda x: -x[1][0]):
    print(k, v[:7], v[7])
print('n', len(seen))
import json
rows = ex.read_tsv(ex.OUT)
dump = []
for k, v in seen.items():
    w, h = v[3], v[4]
    lim = max(v[5], 31 * w)
    dump.append({'key': k, 'lim': lim, 'h': h, 'en': rows[k]['en'], 'ko': rows[k]['ko']})
if len(sys.argv) > 1:
    json.dump(dump, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
