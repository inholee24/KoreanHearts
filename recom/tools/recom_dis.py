"""Re:COM exe 디스어셈블 (읽기 전용).
사용: python -I recom_dis.py <rva_hex> [길이_hex=0x200]
      python -I recom_dis.py --grep <시작_hex> <끝_hex> <정규식>   (구간에서 명령 검색, 함수 경계 무시)
"""
import re, sys
import capstone, pefile

EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe"
pe = pefile.PE(EXE, fast_load=True)
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

if sys.argv[1] == "--grep":
    a, e, pat = int(sys.argv[2], 16), int(sys.argv[3], 16), re.compile(sys.argv[4])
    pos = a
    while pos < e:
        n = 0
        for i in md.disasm(img[pos:e], pos):
            n = i.address + i.size
            s = f"{i.mnemonic} {i.op_str}"
            if pat.search(s):
                print(hex(i.address), s)
        pos = max(n, pos + 1)
else:
    a = int(sys.argv[1], 16)
    ln = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x200
    for i in md.disasm(img[a:a + ln], a):
        print(hex(i.address), i.mnemonic, i.op_str)
