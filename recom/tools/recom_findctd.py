"""CTD 메시지 조회 코드 후보: 같은 레지스터에서 [r+8] 과 [r+0xc] 를 읽고, 근처에 *4 인덱싱이 있는 함수.
사용: python -I recom_findctd.py
"""
import re
import capstone, pefile

EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe"
FUNCS = r"D:\Projects\openkh\re_index_recom\functions.tsv"
pe = pefile.PE(EXE, fast_load=True)
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
for line in open(FUNCS, encoding="utf-8").readlines()[1:]:
    f = line.split("\t")
    a, e = int(f[0], 16), int(f[1], 16)
    if e - a > 0x300:
        continue
    ins = list(md.disasm(img[a:e], a))
    txt = [f"{i.mnemonic} {i.op_str}" for i in ins]
    for k, t in enumerate(txt):
        m = re.match(r"mov \w+, dword ptr \[(r\w+) \+ 0xc\]", t)
        if not m:
            continue
        reg = m.group(1)
        win = " | ".join(txt[max(0, k - 8):k + 8])
        if f"[{reg} + 8]" in win and "*4]" in win:
            print(f"{a:#x} @ {ins[k].address:#x}: {win[:300]}")
            break
