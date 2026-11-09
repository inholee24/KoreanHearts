"""함수 안에서 특정 레지스터(32/64비트 이름 모두)에 값을 쓰는 명령을 모두 보여 준다.
사용: python -I recom_regwrites.py <함수시작_hex> <레지스터(예: edi)> [끝_hex]
"""
import sys
import capstone, pefile

EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe"
FUNCS = r"D:\Projects\openkh\re_index_recom\functions.tsv"
a = int(sys.argv[1], 16)
reg = sys.argv[2]
e = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
if e is None:
    for l in open(FUNCS, encoding="utf-8").readlines()[1:]:
        f = l.split("\t")
        if int(f[0], 16) == a:
            e = int(f[1], 16)
names = {reg}
fam = {"edi": "rdi", "esi": "rsi", "ebx": "rbx", "eax": "rax", "ecx": "rcx", "edx": "rdx"}
names.add(fam.get(reg, reg.rstrip("d")))
pe = pefile.PE(EXE, fast_load=True)
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
for i in md.disasm(img[a:e], a):
    dst = i.op_str.split(",")[0].strip()
    if dst in names and i.mnemonic not in ("cmp", "test", "push") or (i.mnemonic == "pop" and dst in names):
        print(hex(i.address), i.mnemonic, i.op_str)
