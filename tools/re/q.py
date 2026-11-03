"""re_index 조회 도구 (exe 읽기 전용).

사용:  D:\\Projects\\openkh_venv\\Scripts\\python -I tools/re/q.py <명령> ...

  f <rva>            rva 를 포함하는 함수: 크기, 호출자(호출 위치), 피호출자, 참조 문자열/데이터
  x <rva>            rva 를 참조하는 곳 (데이터 참조 + 호출)
  s <정규식>         문자열 검색 + 그 문자열을 참조하는 함수
  d <rva> [최대줄]   rva 를 포함하는 함수 전체 디스어셈블 (이름, 문자열, 임포트 주석 포함)
  n [정규식]         names.tsv 에 정리된 이름 목록

이름/설명은 tools/re/names.tsv (rva<TAB>name<TAB>설명) 에 손으로 추가한다.
주소는 모두 RVA (ImageBase 0x140000000).
"""
import bisect, csv, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDX = HERE.parents[1] / "re_index"
EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS FINAL MIX.exe"


def h(x):
    return int(x, 16)


def load_tsv(name):
    with (IDX / name).open(encoding="utf-8") as f:
        return [line.rstrip("\n").split("\t") for line in f]


class DB:
    def __init__(self):
        rows = load_tsv("functions.tsv")[1:]
        self.funcs = sorted((h(r[0]), h(r[1])) for r in rows)
        self.starts = [a for a, _ in self.funcs]
        self.strings = {h(r[0]): r[3] if len(r) > 3 else "" for r in load_tsv("strings.tsv")}
        self.imports = {h(r[0]): f"{r[1]}!{r[2]}" for r in load_tsv("imports.tsv")}
        self.names = {}
        nf = HERE / "names.tsv"
        if nf.exists():
            for r in load_tsv_path(nf):
                if r and not r[0].startswith("#") and len(r) >= 2:
                    self.names[h(r[0])] = (r[1], r[2] if len(r) > 2 else "")

    def func_of(self, rva):
        i = bisect.bisect_right(self.starts, rva) - 1
        if i >= 0 and self.funcs[i][0] <= rva < self.funcs[i][1]:
            return self.funcs[i]
        return None

    def label(self, rva):
        if rva in self.names:
            return self.names[rva][0]
        if rva in self.imports:
            return self.imports[rva]
        if rva in self.strings:
            return repr(self.strings[rva][:50])
        f = self.func_of(rva)
        if f and f[0] in self.names:
            return f"{self.names[f[0]][0]}+{rva - f[0]:#x}"
        return ""


def load_tsv_path(p):
    with p.open(encoding="utf-8") as f:
        return [line.rstrip("\n").split("\t") for line in f if line.strip()]


def cmd_f(db, rva):
    f = db.func_of(rva)
    if not f:
        print("함수 없음"); return
    a, b = f
    nm = db.names.get(a, ("", ""))
    print(f"func {a:#x}-{b:#x} size {b - a}  {nm[0]}  {nm[1]}")
    calls = load_tsv("calls.tsv")
    print("callers:")
    for c in calls:
        if h(c[2]) == a:
            print(f"  {c[1]} in {c[0]} {db.label(h(c[0]))}  ({c[3]})")
    print("callees:")
    seen = set()
    for c in calls:
        if h(c[0]) == a and c[2] not in seen:
            seen.add(c[2]); print(f"  {c[2]} {db.label(h(c[2])) if not c[3].startswith('call [') else c[3]}")
    print("refs:")
    for r in load_tsv("refs.tsv"):
        if h(r[0]) == a:
            print(f"  {r[1]} -> {r[2]} {r[3]:3} {db.label(h(r[2]))}   ; {r[5]}")


TABLE_SPAN = 0x800  # 포인터에서 이만큼 앞까지 코드가 참조하는 표 시작을 찾는다


def ptr_holders(rva):
    return [h(p[0]) for p in load_tsv("ptrs.tsv") if h(p[1]) == rva]


def table_users(refs_by_target, sorted_targets, where):
    """데이터 위치 where 를 포함하는 표: where 이하에서 코드가 참조하는 가장 가까운 주소."""
    i = bisect.bisect_right(sorted_targets, where) - 1
    if i >= 0 and where - sorted_targets[i] <= TABLE_SPAN:
        t = sorted_targets[i]
        return t, sorted(refs_by_target[t])
    return None, []


def refs_index():
    by = defaultdict(set)
    for r in load_tsv("refs.tsv"):
        by[h(r[2])].add(r[0])
    return by, sorted(by)


def cmd_x(db, rva):
    for r in load_tsv("refs.tsv"):
        if h(r[2]) == rva:
            print(f"ref  {r[1]} in {r[0]} {db.label(h(r[0]))}  {r[3]}  ; {r[5]}")
    for c in load_tsv("calls.tsv"):
        if h(c[2]) == rva:
            print(f"call {c[1]} in {c[0]} {db.label(h(c[0]))}")
    by, st = refs_index()
    for p in ptr_holders(rva):
        t, users = table_users(by, st, p)
        tb = f"table {t:#x}+{p - t:#x} used by {', '.join(users)}" if t is not None else "table ?"
        print(f"ptr  at {p:#x}  ({tb})")


def cmd_s(db, pat):
    rx = re.compile(pat)
    hits = {a: s for a, s in db.strings.items() if rx.search(s)}
    by, st = refs_index()
    holders = defaultdict(list)
    for p in load_tsv("ptrs.tsv"):
        t = h(p[1])
        if t in hits:
            holders[t].append(h(p[0]))
    for a in sorted(hits):
        direct = sorted(by.get(a, ()))
        line = f"{a:#x} {hits[a]!r}  <- {', '.join(direct) or '-'}"
        for p in holders[a][:3]:
            t, users = table_users(by, st, p)
            if t is not None:
                line += f"  [ptr {p:#x} = tbl {t:#x}+{p - t:#x} <- {', '.join(users[:4])}]"
            else:
                line += f"  [ptr {p:#x}]"
        print(line)


def cmd_d(db, rva, limit=4000):
    import capstone, pefile
    f = db.func_of(rva)
    if not f:
        print("함수 없음"); return
    a, b = f
    pe = pefile.PE(EXE, fast_load=True)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    print(f"; func {a:#x}-{b:#x} {db.label(a)}")
    for k, ins in enumerate(md.disasm(pe.get_data(a, b - a), a)):
        if k >= limit:
            break
        note = ""
        for op in ins.operands:
            t = None
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                t = ins.address + ins.size + op.mem.disp
            elif op.type == capstone.x86.X86_OP_IMM and (ins.mnemonic == "call" or ins.mnemonic.startswith("j")):
                t = op.imm
            if t is not None:
                lb = db.label(t)
                note = f"  ; {t:#x} {lb}" if not (a <= t < b) or lb else ""
        if ins.address in db.names:
            print(f"{db.names[ins.address][0]}:")
        print(f"  {ins.address:#x}: {ins.mnemonic} {ins.op_str}{note}")


def cmd_n(db, pat="."):
    rx = re.compile(pat)
    for a in sorted(db.names):
        n, d = db.names[a]
        if rx.search(n) or rx.search(d):
            print(f"{a:#x}\t{n}\t{d}")


def main(argv):
    if not argv:
        print(__doc__); return 2
    db = DB()
    c = argv[0]
    if c == "f": cmd_f(db, h(argv[1]))
    elif c == "x": cmd_x(db, h(argv[1]))
    elif c == "s": cmd_s(db, argv[1])
    elif c == "d": cmd_d(db, h(argv[1]), int(argv[2]) if len(argv) > 2 else 4000)
    elif c == "n": cmd_n(db, argv[1] if len(argv) > 1 else ".")
    else: print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
