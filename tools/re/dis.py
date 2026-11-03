"""KH1 exe 지정 RVA 구간 디스어셈블 (읽기 전용).
사용: openkh_venv python tools/re/dis.py <rva_hex> [앞쪽바이트=0x40] [뒤쪽바이트=0x80]
"""
import sys, pefile, capstone
EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS FINAL MIX.exe"
rva = int(sys.argv[1], 16)
back = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x40
fwd = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x80
pe = pefile.PE(EXE, fast_load=True)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
start = rva - back
data = pe.get_data(start, back + fwd)
for ins in md.disasm(data, start):
    mark = ">>" if ins.address == rva else "  "
    print(f"{mark}{ins.address:#x}: {ins.mnemonic} {ins.op_str}")
