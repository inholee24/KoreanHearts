"""코드 주소 구간을 가리키는 8바이트 포인터(vtable 항목)를 이미지 전체에서 찾고, vtable[-1] 의 RTTI 로 클래스 이름을 읽는다.
사용: python -I recom_vtable.py <시작_hex> <끝_hex>
"""
import struct, sys
import pefile

EXE = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe"
pe = pefile.PE(EXE, fast_load=True)
img = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)


def rtti_name(vt):
    """vtable RVA -> 클래스 이름 (MSVC x64: vt[-1] = COL, COL+0xC = TypeDescriptor RVA, TD+0x10 = 이름)."""
    try:
        col = struct.unpack_from("<Q", img, vt - 8)[0] - base
        if not (0 < col < len(img)) or struct.unpack_from("<I", img, col)[0] != 1:
            return None
        td = struct.unpack_from("<I", img, col + 0xC)[0]
        name = img[td + 0x10: td + 0x80].split(b"\0")[0]
        return name.decode("ascii", "replace")
    except struct.error:
        return None


seen = {}
for off in range(0, len(img) - 8, 8):
    v = struct.unpack_from("<Q", img, off)[0] - base
    if lo <= v < hi:
        # vtable 시작 찾기: 앞으로 가며 코드 포인터가 끊기는 곳
        s = off
        while s >= 8:
            p = struct.unpack_from("<Q", img, s - 8)[0] - base
            if not (0x1000 <= p < 0x500000):
                break
            s -= 8
        nm = rtti_name(s)
        seen.setdefault((s, nm), []).append((off, v))
for (s, nm), items in sorted(seen.items()):
    print(f"vtable {s:#x} {nm}: " + ", ".join(f"[{(o - s) // 8}]={v:#x}" for o, v in items[:10]))
