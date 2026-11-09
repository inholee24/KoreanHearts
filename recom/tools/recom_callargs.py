"""함수 호출 직전에 [rsp + off] 에 쓰는 값을 호출부마다 보여 준다 (스택 인자 추적).
사용: python -I recom_callargs.py <callee_hex> <off_hex> [앞쪽 명령 수=30]
"""
import re, sys
import capstone, pefile

EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe"
CALLS = r"D:\Projects\openkh\re_index_recom\calls.tsv"
callee, off = sys.argv[1].lower(), int(sys.argv[2], 16)
back = int(sys.argv[3]) if len(sys.argv) > 3 else 30
pe = pefile.PE(EXE, fast_load=True)
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
sites = [(int(l.split("\t")[0], 16), int(l.split("\t")[1], 16)) for l in open(CALLS, encoding="utf-8") if l.split("\t")[2].strip().startswith(callee)]
pat = re.compile(rf"\[rsp \+ {off:#x}\], (.+)$")
for func, site in sites:
    ins = [i for i in md.disasm(img[func:site + 5], func)]
    idx = next((k for k, i in enumerate(ins) if i.address == site), None)
    if idx is None:
        print(f"{site:#x}: 디스어셈블 실패"); continue
    val = None
    for i in reversed(ins[max(0, idx - back):idx]):
        m = pat.search(i.op_str)
        if i.mnemonic == "mov" and m:
            val = m.group(1)
            if not val.startswith("0x") and not val.isdigit():   # 레지스터면 그 레지스터를 정한 명령도 찾아본다
                reg = val
                for j in reversed(ins[max(0, idx - back * 2):ins.index(i)]):
                    if j.mnemonic in ("mov", "lea", "or") and j.op_str.startswith(reg + ","):
                        val = f"{reg} <- {j.mnemonic} {j.op_str}"; break
            break
    print(f"{func:#x} {site:#x}: {val}")
