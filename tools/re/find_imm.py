"""KH1 exe .text에서 특정 즉값/변위를 쓰는 명령어를 찾는다 (읽기 전용).
사용: openkh_venv python tools/re/find_imm.py <hex값> [<hex값> ...]
"""
import sys, pefile, capstone
EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS FINAL MIX.exe"
vals = {int(v, 16) & 0xFFFFFFFFFFFFFFFF for v in sys.argv[1:]}
pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); md.detail = True
for s in pe.sections:
    if not s.Characteristics & 0x20000000: continue
    code = s.get_data(); va = base + s.VirtualAddress
    off = 0
    while off < len(code):
        got = False
        for ins in md.disasm(code[off:off+0x10000], va + off):
            got = True
            for op in ins.operands:
                v = None
                if op.type == capstone.x86.X86_OP_IMM: v = op.imm
                elif op.type == capstone.x86.X86_OP_MEM: v = op.mem.disp
                if v is not None and ((v & 0xFFFFFFFF) in vals or (v & 0xFFFFFFFFFFFFFFFF) in vals):
                    print(f"{ins.address - base:#x}: {ins.mnemonic} {ins.op_str}")
            last = ins.address + ins.size - va
        off = last if got and last > off else off + 1
