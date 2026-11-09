"""함수별로 [reg + off] 읽기 오프셋 집합을 모아, 주어진 오프셋들을 모두 읽는 함수를 찾는다 (구조체 소비 함수 찾기).
사용: python -I recom_findfields.py <오프셋,...> [최소 일치 수]
예:   recom_findfields.py 0x16,0x18,0x1a,0x1c,0x1e,0x20,0x22 6
"""
import re, sys
import capstone, pefile

EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe"
FUNCS = r"D:\Projects\openkh\re_index_recom\functions.tsv"
want = [int(x, 16) for x in sys.argv[1].split(",")]
need = int(sys.argv[2]) if len(sys.argv) > 2 else len(want)
pe = pefile.PE(EXE, fast_load=True)
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
pat = re.compile(r"(?:byte|word|dword) ptr \[(r\w+) \+ (0x[0-9a-f]+)\]")
for line in open(FUNCS, encoding="utf-8").readlines()[1:]:
    f = line.split("\t")
    a, e = int(f[0], 16), int(f[1], 16)
    if e - a > 0x4000:
        continue
    per_reg = {}
    for i in md.disasm(img[a:e], a):
        if not i.mnemonic.startswith(("mov", "cmp", "test")):
            continue
        for reg, off in pat.findall(i.op_str):
            if reg in ("rsp", "rbp", "rip"):
                continue
            per_reg.setdefault(reg, set()).add(int(off, 16))
    best = max((len(s & set(want)), r) for r, s in per_reg.items()) if per_reg else (0, None)
    if best[0] >= need:
        print(f"{a:#x} size {e - a:#x} reg {best[1]} hits {best[0]}")
