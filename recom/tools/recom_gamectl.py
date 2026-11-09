"""게임 창 조작·캡처 (게임 안 확인용). KH1 때 방식(memory: F24 로 포커스, 스캔코드 SendInput)을 다시 만든 것.

사용 (openkh_venv python -X utf8):
  recom_gamectl.py windows                         보이는 창 목록 (pid, exe, 제목, 크기)
  recom_gamectl.py launch                           Re:COM 실행 파일 실행 (Steam 이 런처를 띄울 수 있음)
  recom_gamectl.py shot <exe부분이름> <png>          그 프로세스의 가장 큰 창 클라이언트 영역 캡처
  recom_gamectl.py keys <exe부분이름> <키...>        포커스 후 키 입력. 키: up down left right enter esc space
                                                     w a s d f, 'wait:초', 키*횟수 (예: down*2)
주의: 게임에 WM_SYSCOMMAND 를 보내지 않는다 (종료 창). Alt 대신 F24 로 포커스를 얻는다.
"""
import ctypes, ctypes.wintypes as wt, os, subprocess, sys, time

GAME = r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-"
EXE = "KINGDOM HEARTS Re_Chain of Memories.exe"
u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

SC = {"esc": 0x01, "enter": 0x1C, "space": 0x39, "w": 0x11, "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21,
      "q": 0x10, "e": 0x12, "up": (0x48, True), "down": (0x50, True), "left": (0x4B, True), "right": (0x4D, True),
      "backspace": 0x0E, "tab": 0x0F}


class KI(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class INP(ctypes.Structure):
    class U(ctypes.Union):
        _fields_ = [("ki", KI), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", U)]


def send(vk=0, scan=0, flags=0):
    i = INP(type=1)
    i.ki = KI(vk, scan, flags, 0, 0)
    u32.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))


def tap(name, hold=0.08):
    v = SC[name]
    sc, ext = (v if isinstance(v, tuple) else (v, False))
    f = 0x0008 | (0x0001 if ext else 0)          # KEYEVENTF_SCANCODE (+ EXTENDED)
    send(scan=sc, flags=f)
    time.sleep(hold)
    send(scan=sc, flags=f | 0x0002)               # KEYUP


def exe_of(pid):
    h = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    buf = ctypes.create_unicode_buffer(1024)
    n = wt.DWORD(1024)
    ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
    k32.CloseHandle(h)
    return os.path.basename(buf.value) if ok else ""


def windows():
    out = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        if u32.IsWindowVisible(h):
            pid = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            r = wt.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            t = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(h, t, 256)
            out.append((h, pid.value, exe_of(pid.value), t.value, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0)
    return out


def find(part):
    c = [w for w in windows() if part.lower() in w[2].lower() and w[4] * w[5] > 0]
    return max(c, key=lambda w: w[4] * w[5]) if c else None


def focus(h):
    send(vk=0x87); send(vk=0x87, flags=0x0002)    # F24: SetForegroundWindow 허용용 입력
    u32.SetForegroundWindow(h)
    time.sleep(0.3)


def shot(h, png):
    from PIL import ImageGrab
    r = wt.RECT()
    u32.GetClientRect(h, ctypes.byref(r))
    p = wt.POINT(0, 0)
    u32.ClientToScreen(h, ctypes.byref(p))
    ImageGrab.grab((p.x, p.y, p.x + r.right, p.y + r.bottom), all_screens=True).save(png)
    return r.right, r.bottom


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "windows":
        for w in windows():
            if w[4] * w[5] > 0:
                print(w[1], w[2], repr(w[3]), f"{w[4]}x{w[5]}")
    elif c == "launch":
        subprocess.Popen([os.path.join(GAME, EXE)], cwd=GAME)
        print("launched")
    elif c in ("shot", "keys"):
        w = find(sys.argv[2])
        if not w:
            raise SystemExit(f"창 없음: {sys.argv[2]}")
        if c == "shot":
            print("captured", shot(w[0], sys.argv[3]), w[2])
        else:
            focus(w[0])
            for k in sys.argv[3:]:
                if k.startswith("wait:"):
                    time.sleep(float(k[5:]))
                    continue
                name, _, n = k.partition("*")
                for _ in range(int(n or 1)):
                    tap(name)
                    time.sleep(0.35)
            print("sent", sys.argv[3:])
