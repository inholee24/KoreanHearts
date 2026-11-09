"""KH1 exe에서 RIP 상대 주소로 특정 RVA를 참조하는 명령어를 찾는다 (읽기 전용).
사용: openkh_venv python tools/re/find_ref.py <rva_hex> [...]
"""
import sys, pefile, capstone
EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS FINAL MIX.exe"
targets = {int(v, 16) for v in sys.argv[1:]}
pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); md.detail = True
for s in pe.sections:
    if not s.Characteristics & 0x20000000: continue
    code = s.get_data(); va = s.VirtualAddress
    off = 0
    while off < len(code):
        last = off
        for ins in md.disasm(code[off:off+0x10000], va + off):
            for op in ins.operands:
                if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                    ea = ins.address + ins.size + op.mem.disp
                    if ea in targets:
                        print(f"{ins.address:#x}: {ins.mnemonic} {ins.op_str}   ; -> {ea:#x}")
            last = ins.address + ins.size - va
        off = last if last > off else off + 1
