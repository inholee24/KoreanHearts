"""같은 레지스터에 여러 오프셋을 '쓰는' 함수 찾기 (구조체 생성자 찾기).
사용: python -I recom_findwriters.py <오프셋,...> [최소 일치 수]
"""
import re, sys
import capstone, pefile

EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe"
FUNCS = r"D:\Projects\openkh\re_index_recom\functions.tsv"
want = {int(x, 16) for x in sys.argv[1].split(",")}
need = int(sys.argv[2]) if len(sys.argv) > 2 else len(want)
pe = pefile.PE(EXE, fast_load=True)
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
pat = re.compile(r"^(?:dword|qword) ptr \[(r\w+) \+ (0x[0-9a-f]+)\],")
for line in open(FUNCS, encoding="utf-8").readlines()[1:]:
    f = line.split("\t")
    a, e = int(f[0], 16), int(f[1], 16)
    if e - a > 0x3000:
        continue
    per = {}
    for i in md.disasm(img[a:e], a):
        if i.mnemonic != "mov":
            continue
        m = pat.match(i.op_str)
        if m and m.group(1) not in ("rsp", "rbp", "rip"):
            per.setdefault(m.group(1), set()).add(int(m.group(2), 16))
    for r, s in per.items():
        if len(s & want) >= need:
            print(f"{a:#x} size {e - a:#x} reg {r} {sorted(hex(x) for x in s & want)}")
