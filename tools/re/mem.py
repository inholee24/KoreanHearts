"""실행 중인 KH1 프로세스 메모리 읽기 (읽기 전용).

사용:  D:\\Projects\\openkh_venv\\Scripts\\python -I tools/re/mem.py <명령> ...
  win                창 슬롯 4개(0x23D4220)와 템플릿 8개(0x23D4560) 필드 요약
  rd <rva> <len>     RVA 에서 len 바이트 hex 덤프
  watch [초]         win 을 0.5초마다 반복, 바뀐 줄만 출력 (기본 20초)
  find <hex> [ctx]   프로세스 전체 메모리에서 바이트 열 검색 (ctx 바이트 앞뒤 문맥 출력)
  sf                 시스템 글꼴 확인 (40차): 텍스처(TBP 0x1000) +0x7c/+0x94 크기, 표 버퍼(0x2E16BF0)가
                     mod/kh1/exchange/US_font_data_tbl.bin 과 같은지
  tex2x [초] [new]   [쓰기] 대화창 글꼴 텍스처(kanji_tex 0x22EC3C8 의 +0x94/+0x96)가 512x512 이면
                     1024x1024 로 바꾼다 (일본어판과 같은 처리). 초 동안 감시하며 되돌아가면 다시 쓴다 (기본 1800).
                     new: 지금 실행 중인 게임은 건너뛰고 새로 켜진 게임에만 적용
                     jp: 대화창 글꼴 배치도 일본어판으로 (페이지당 줄 0x4DE830=21, 줄 높이 0x4DE834=24,
                         글자 수 0x2340BA8=1764). build_ko.py --layout jp 로 만든 DDS 와 함께 쓴다 (28차)
                     진단용 (55차): nocode = JP_CODE 패치 빼기, nosf = 시스템 글꼴 표 확장 빼기

주소는 RVA (exe 모듈 베이스 기준). 쓰기는 tex2x 뿐이며 게임을 다시 켜면 원래대로 돌아간다.
"""
import ctypes, ctypes.wintypes as wt, struct, sys, time

EXE_NAME = "KINGDOM HEARTS FINAL MIX.exe"
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
TH32CS_SNAPPROCESS, TH32CS_SNAPMODULE = 0x2, 0x8
PROCESS_VM_READ, PROCESS_QUERY_INFORMATION = 0x10, 0x400
PROCESS_VM_WRITE, PROCESS_VM_OPERATION = 0x20, 0x8
KANJI_TEX = 0x22EC3C8
OFF = set()   # tex2x 진단용으로 뺄 항목


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE), ("szModule", wt.WCHAR * 256),
                ("szExePath", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]


def attach(write=False):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PROCESSENTRY32W(); pe.dwSize = ctypes.sizeof(pe)
    pid = None
    ok = k32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        if pe.szExeFile.lower() == EXE_NAME.lower():
            pid = pe.th32ProcessID
        ok = k32.Process32NextW(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    if pid is None:
        sys.exit(f"{EXE_NAME} 프로세스가 없다")
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
    me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
    base = None
    ok = k32.Module32FirstW(snap, ctypes.byref(me))
    while ok:
        if me.szModule.lower() == EXE_NAME.lower():
            base = me.modBaseAddr
        ok = k32.Module32NextW(snap, ctypes.byref(me))
    k32.CloseHandle(snap)
    access = PROCESS_VM_READ | PROCESS_QUERY_INFORMATION | (PROCESS_VM_WRITE | PROCESS_VM_OPERATION if write else 0)
    h = k32.OpenProcess(access, False, pid)
    if not h or base is None:
        sys.exit(f"프로세스 열기 실패 (pid {pid}, err {ctypes.get_last_error()})")
    return h, base, pid


def rd(h, base, rva, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + rva), buf, n, ctypes.byref(got)):
        raise OSError(f"read {rva:#x} 실패 err {ctypes.get_last_error()}")
    return buf.raw[:got.value]


def rd_abs(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)) or got.value != n:
        raise OSError(f"read {addr:#x} 실패 err {ctypes.get_last_error()}")
    return buf.raw


def wr_abs(h, addr, data):
    got = ctypes.c_size_t()
    k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    if not k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(got)) or got.value != len(data):
        raise OSError(f"write {addr:#x} 실패 err {ctypes.get_last_error()}")


def wr_code(h, addr, data):
    """코드 페이지 쓰기: 보호를 잠시 RWX 로 바꿨다가 되돌린다."""
    old = wt.DWORD()
    k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, ctypes.POINTER(wt.DWORD)]
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), 0x40, ctypes.byref(old)):
        raise OSError(f"protect {addr:#x} 실패 err {ctypes.get_last_error()}")
    try:
        wr_abs(h, addr, data)
    finally:
        k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(wt.DWORD()))
        k32.FlushInstructionCache.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
        k32.FlushInstructionCache(h, ctypes.c_void_p(addr), len(data))


def find_pid():
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PROCESSENTRY32W(); pe.dwSize = ctypes.sizeof(pe)
    pid = None
    ok = k32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        if pe.szExeFile.lower() == EXE_NAME.lower():
            pid = pe.th32ProcessID
        ok = k32.Process32NextW(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return pid


JP_LAYOUT = ((0x4DE830, 21), (0x4DE834, 24), (0x2340BA8, 1764))   # font_lang_setup 0x18D130 의 일본어 값
# 시스템 글꼴 표 확장 (43차): 게임은 표 파일을 정적 버퍼 0x2E16BF0 (1024 레코드) 에 읽고 포인터 0x2E16BE0 를 거쳐
# 쓴다 (font_tbl_init 0x2d1570 외에는 모두 포인터). 전체 표(translation/build/sysfont_tbl_full.bin)를 게임 안에
# 새로 잡은 버퍼에 쓰고 포인터를 바꾼다. Shift-JIS 찾기 레코드 수 0x2E16BE8 (원래 560) 도 전체 수로.
SF_PTR, SF_STATIC, SF_COUNT = 0x2E16BE0, 0x2E16BF0, 0x2E16BE8
SF_FULL = __import__("os").path.join(__import__("os").environ.get("KH1KO_ROOT") or __import__("os").path.join(__import__("os").path.dirname(__file__), "..", ".."), "translation", "build", "sysfont_tbl_full.bin")
# kanji_cell_xy 0x176021: 비일본어·크기!=20 글자(장소 이름 등)의 화면 높이 = [0x4DE834]. jp 배치에서 24 가 되어
# 글자가 세로로 눌린다 (31차) -> 영어판 값 32 로 고정. mov eax,[rip+0x36880d] -> mov eax,32; nop
JP_CODE = ((0x176021, bytes.fromhex("8B050D883600"), bytes.fromhex("B82000000090")),)


def tex2x_main(secs, only_new, jp=False):
    end = time.time() + secs
    skip = find_pid() if only_new else None
    if skip:
        print(f"실행 중인 pid {skip} 는 건너뜀. 새 게임 대기", flush=True)
    while time.time() < end:
        pid = find_pid()
        if pid is None or pid == skip:
            time.sleep(0.5); continue
        try:
            h, base, pid = attach(write=True)
        except (SystemExit, OSError, ctypes.ArgumentError):
            time.sleep(0.5); continue
        print(f"pid {pid} base {base:#x}", flush=True)
        try:
            tex2x(h, base, end - time.time(), jp)
        except OSError as e:
            print(f"[{time.strftime('%H:%M:%S')}] 연결 끊김 ({e}). 다시 대기", flush=True)
        skip = pid


def tex2x(h, base, secs, jp=False):
    """kanji_tex 의 폭/높이 word 를 512 -> 1024 로. kanji_load(0x176430) 의 일본어 분기와 같은 효과."""
    end, last, last_code = time.time() + secs, None, {}
    full = open(SF_FULL, "rb").read() if jp and "nosf" not in OFF else b""
    sf_buf = None
    while time.time() < end:
        if full:
            ptr = struct.unpack("<Q", rd(h, base, SF_PTR, 8))[0]
            if ptr == base + SF_STATIC:
                if sf_buf is None:
                    k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
                    k32.VirtualAllocEx.restype = ctypes.c_void_p
                    sf_buf = k32.VirtualAllocEx(h, None, len(full), 0x3000, 0x04)
                    if not sf_buf:
                        raise OSError(f"VirtualAllocEx 실패 err {ctypes.get_last_error()}")
                wr_abs(h, sf_buf, full)
                wr_abs(h, base + SF_PTR, struct.pack("<Q", sf_buf))
                print(f"[{time.strftime('%H:%M:%S')}] sysfont 표 {len(full) // 16} 레코드 -> {sf_buf:#x}", flush=True)
            cur = struct.unpack("<i", rd(h, base, SF_COUNT, 4))[0]
            if ptr and cur != len(full) // 16:
                wr_abs(h, base + SF_COUNT, struct.pack("<i", len(full) // 16))
                print(f"[{time.strftime('%H:%M:%S')}] {SF_COUNT:#x}: {cur} -> {len(full) // 16}", flush=True)
        for rva, val in (JP_LAYOUT if jp else ()):
            cur = struct.unpack("<i", rd(h, base, rva, 4))[0]
            if cur != val:
                wr_abs(h, base + rva, struct.pack("<i", val))
                print(f"[{time.strftime('%H:%M:%S')}] {rva:#x}: {cur} -> {val}", flush=True)
        for rva, old, new in (JP_CODE if jp and "nocode" not in OFF else ()):
            cur = rd(h, base, rva, len(old))
            if cur == old:
                wr_code(h, base + rva, new)
                print(f"[{time.strftime('%H:%M:%S')}] code {rva:#x}: {old.hex()} -> {rd(h, base, rva, len(new)).hex()}", flush=True)
            elif cur != new and (rva, cur) != last_code.get(rva):
                print(f"[{time.strftime('%H:%M:%S')}] code {rva:#x}: 예상 밖 바이트 {cur.hex()} -> 건드리지 않음", flush=True)
                last_code[rva] = (rva, cur)
        ptr =struct.unpack("<Q", rd(h, base, KANJI_TEX, 8))[0]
        state = (ptr, None)
        if ptr:
            w, hh = struct.unpack("<2H", rd_abs(h, ptr + 0x94, 4))
            state = (ptr, (w, hh))
            if (w, hh) == (512, 512):
                wr_abs(h, ptr + 0x94, struct.pack("<2H", 1024, 1024))
                w2 = struct.unpack("<2H", rd_abs(h, ptr + 0x94, 4))
                print(f"[{time.strftime('%H:%M:%S')}] tex {ptr:#x}: 512x512 -> {w2[0]}x{w2[1]}", flush=True)
                state = (ptr, w2)
        if state != last:
            print(f"[{time.strftime('%H:%M:%S')}] kanji_tex={ptr:#x} size={state[1]}", flush=True)
            last = state
        time.sleep(0.2)


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p), ("AllocationProtect", wt.DWORD),
                ("PartitionId", wt.WORD), ("RegionSize", ctypes.c_size_t), ("State", wt.DWORD),
                ("Protect", wt.DWORD), ("Type", wt.DWORD)]


def scan(h, pat):
    """읽을 수 있는 커밋 영역 전체에서 pat 위치를 찾는다 (절대 주소)."""
    k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
    k32.VirtualQueryEx.restype = ctypes.c_size_t
    addr, mbi = 0, MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base, size = mbi.BaseAddress or 0, mbi.RegionSize
        readable = mbi.State == 0x1000 and not (mbi.Protect & 0x101) and (mbi.Protect & 0xEE)
        if readable and size < (1 << 31):
            buf = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t()
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)):
                data = buf.raw[:got.value]
                i = data.find(pat)
                while i >= 0:
                    yield base + i, base, data
                    i = data.find(pat, i + 1)
        addr = base + size
        if addr >= 1 << 47:
            break


def fmt_struct(b):
    w = struct.unpack_from("<4H", b, 0)
    f = struct.unpack_from("<12f", b, 0x20)
    fl = " ".join(f"{x:8.2f}" for x in f)
    return f"w0-6={w} +20..+4C: {fl}"


def win_summary(h, base):
    lines = []
    st = rd(h, base, 0x237F4F0, 8)
    qc = struct.unpack("<4i", rd(h, base, 0x2380500, 16))
    lines.append(f"win_state={list(st[:4])} slot_flag={list(st[4:8])} qcount={qc}")
    for i in range(4):
        lines.append(f"slot{i}: " + fmt_struct(rd(h, base, 0x23D4220 + i * 0xD0, 0xD0)))
    for i in range(8):
        lines.append(f"tpl{i}:  " + fmt_struct(rd(h, base, 0x23D4560 + i * 0xD0, 0xD0)))
    return lines


def main(argv):
    if not argv:
        print(__doc__); return 2
    if argv[0] == "tex2x":
        OFF.update(a for a in argv[2:] if a in ("nocode", "nosf"))
        print(f"끔: {sorted(OFF) or '없음'}", flush=True)
        tex2x_main(float(argv[1]) if len(argv) > 1 else 1800, "new" in argv[2:], "jp" in argv[2:])
        return 0
    h, base, pid = attach()
    print(f"pid {pid} base {base:#x}")
    c = argv[0]
    if c == "win":
        print("\n".join(win_summary(h, base)))
    elif c == "rd":
        rva, n = int(argv[1], 16), int(argv[2], 0)
        b = rd(h, base, rva, n)
        for i in range(0, len(b), 16):
            print(f"{rva + i:#x}: {b[i:i + 16].hex(' ')}")
    elif c == "find":
        pat = bytes.fromhex(argv[1])
        ctx = int(argv[2], 0) if len(argv) > 2 else 0
        for addr, chunk_addr, chunk in scan(h, pat):
            off = addr - chunk_addr
            print(f"{addr:#x}" + (f"  ctx {chunk[max(0, off - ctx):off + len(pat) + ctx].hex()}" if ctx else ""))
    elif c == "sf":
        head = struct.unpack("<Q", rd(h, base, 0x22C8FC0, 8))[0]
        seen, stack = set(), [struct.unpack("<Q", rd_abs(h, head, 0x40)[8:16])[0]]
        while stack:                                   # std::map 순회: [0] 왼쪽 [0x10] 오른쪽 [0x19] nil [0x20] 키 [0x30] 값
            p = stack.pop()
            nb = rd_abs(h, p, 0x40)
            if nb[0x19] or p in seen:
                continue
            seen.add(p)
            stack += [struct.unpack_from("<Q", nb, 0)[0], struct.unpack_from("<Q", nb, 0x10)[0]]
            key, tex = struct.unpack_from("<Q", nb, 0x20)[0], struct.unpack_from("<Q", nb, 0x30)[0]
            if key >> 48 == 0x1000:
                t = rd_abs(h, tex, 0x98)
                print(f"sysfont tex {tex:#x} psm {(key >> 32) & 0xffff:#x} +7c {struct.unpack_from('<2H', t, 0x7c)} +94 {struct.unpack_from('<2H', t, 0x94)}")
        import os
        f = open(os.path.join(os.path.dirname(__file__), "..", "..", "mod", "kh1", "exchange", "US_font_data_tbl.bin"), "rb").read()
        m = rd(h, base, 0x2E16BF0, len(f))
        print(f"표 버퍼 {len(f)}B: mod 파일과 {'같음' if m == f else '다름 (첫 차이 ' + str(next(i for i in range(len(f)) if m[i] != f[i])) + ')'}")
    elif c == "watch":
        end = time.time() + (float(argv[1]) if len(argv) > 1 else 20)
        prev = []
        while time.time() < end:
            cur = win_summary(h, base)
            for i, l in enumerate(cur):
                if i >= len(prev) or prev[i] != l:
                    print(f"[{time.strftime('%H:%M:%S')}] {l}")
            prev = cur
            time.sleep(0.5)
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
